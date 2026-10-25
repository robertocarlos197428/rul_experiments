from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import logging
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parents[1]
PROC_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
DOCS_DIR = BASE_DIR / "docs"
RESULTS_DIR = BASE_DIR / "results" / "005_train"
MODELS_DIR = BASE_DIR / "models"

for d in [LOG_DIR, DOCS_DIR, RESULTS_DIR, MODELS_DIR, PROC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

STEM = Path(__file__).stem
LOG_FILE = LOG_DIR / f"{STEM}.log"
MD_FILE = DOCS_DIR / f"{STEM}.md"
MODEL_FILE = MODELS_DIR / "005_best_model.pt"
NPZ_FILE = PROC_DIR / f"{STEM}.npz"
REPORTE_FILE = RESULTS_DIR / "reporte.txt"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s')
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

# Carga con squeeze para tu caso (24889,1,2560) -> (24889,2560)
X_global = np.load(PROC_DIR / "001_build_input.npz")['X']
X_global = np.squeeze(X_global)
print(f"X_global {X_global.shape}")

d3 = np.load(PROC_DIR / "003_build_windows.npz", allow_pickle=True)
windows_idx = d3['windows_idx']
y_windows = d3['y_windows']

d4 = np.load(PROC_DIR / "004_build_datasets.npz", allow_pickle=True)
train_idx, val_idx, test_idx = d4['train_idx'], d4['val_idx'], d4['test_idx']

WINDOW_SIZE = int(d3['window_size'])
print(f"Ventanas {len(windows_idx)} W={WINDOW_SIZE} | Train {len(train_idx)} Val {len(val_idx)} Test {len(test_idx)}")

class RULDataset(Dataset):
    def __init__(self, g_idx, w_idx, y_w, Xg):
        self.g_idx = g_idx
        self.w_idx = w_idx
        self.y_w = y_w
        self.Xg = Xg
    def __len__(self):
        return len(self.g_idx)
    def __getitem__(self, i):
        j = self.g_idx[i]
        s, e = self.w_idx[j]
        x = self.Xg[s:e]
        # Fix por si X viene con dim extra (30,1,2560)
        if x.ndim == 3:
            x = x.squeeze(1)
        y = self.y_w[j]
        x = (x - x.mean(axis=0, keepdims=True)) / (x.std(axis=0, keepdims=True) + 1e-8)
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

train_ds = RULDataset(train_idx, windows_idx, y_windows, X_global)
val_ds = RULDataset(val_idx, windows_idx, y_windows, X_global)
test_ds = RULDataset(test_idx, windows_idx, y_windows, X_global)

train_loader = DataLoader(train_ds, batch_size=64, shuffle=True, num_workers=0)
val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, num_workers=0)
test_loader = DataLoader(test_ds, batch_size=128, shuffle=False, num_workers=0)

class Chomp1d(nn.Module):
    def __init__(self, chomp):
        super().__init__()
        self.chomp = chomp
    def forward(self, x):
        if self.chomp > 0:
            return x[:, :, :-self.chomp].contiguous()
        return x

class TCNBlock(nn.Module):
    def __init__(self, in_c, out_c, k=3, dilation=1, dropout=0.2):
        super().__init__()
        pad = (k-1)*dilation
        self.net = nn.Sequential(
            nn.Conv1d(in_c, out_c, k, padding=pad, dilation=dilation),
            Chomp1d(pad),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(out_c, out_c, k, padding=pad, dilation=dilation),
            Chomp1d(pad),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.down = nn.Conv1d(in_c, out_c, 1) if in_c!= out_c else nn.Identity()
    def forward(self, x):
        return self.net(x) + self.down(x)

class RULNet(nn.Module):
    def __init__(self, in_dim=2560, tcn_c=64, nhead=4, nlayers=2):
        super().__init__()
        self.tcn = nn.Sequential(
            TCNBlock(in_dim, tcn_c, dilation=1),
            TCNBlock(tcn_c, tcn_c, dilation=2),
            TCNBlock(tcn_c, tcn_c, dilation=4)
        )
        enc_layer = nn.TransformerEncoderLayer(d_model=tcn_c, nhead=nhead, dim_feedforward=128, batch_first=True, dropout=0.2)
        self.trans = nn.TransformerEncoder(enc_layer, num_layers=nlayers)
        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(tcn_c, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1)
        )
    def forward(self, x): # x (B,30,2560)
        x = x.transpose(1, 2) # (B,2560,30)
        x = self.tcn(x) # (B,64,30)
        x = x.transpose(1, 2) # (B,30,64)
        x = self.trans(x) # (B,30,64)
        x = x.transpose(1, 2) # (B,64,30)
        return self.head(x).squeeze(1)

model = RULNet().to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
crit = nn.MSELoss()
sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5, factor=0.5)

best_val = float('inf')
patience, bad = 15, 0
hist_train, hist_val = [], []
EPOCHS = 80

for epoch in tqdm(range(EPOCHS), desc="Epocas TCN+Trans"):
    model.train()
    tr_loss = 0
    for xb, yb in train_loader:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        pred = model(xb)
        loss = crit(pred, yb)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        tr_loss += loss.item() * len(xb)
    tr_loss /= len(train_ds)

    model.eval()
    va_loss = 0
    with torch.no_grad():
        for xb, yb in val_loader:
            xb, yb = xb.to(device), yb.to(device)
            va_loss += crit(model(xb), yb).item() * len(xb)
    va_loss /= len(val_ds)
    sched.step(va_loss)

    hist_train.append(tr_loss)
    hist_val.append(va_loss)
    logging.info(f"E{epoch+1} train {tr_loss:.5f} val {va_loss:.5f}")
    tqdm.write(f"E{epoch+1:02d} train {tr_loss:.4f} val {va_loss:.4f}")

    if va_loss < best_val:
        best_val = va_loss
        bad = 0
        torch.save(model.state_dict(), MODEL_FILE)
    else:
        bad += 1
        if bad >= patience:
            print(f"Early stop en epoca {epoch+1}")
            break

# Test final
model.load_state_dict(torch.load(MODEL_FILE, map_location=device))
model.eval()
preds, trues = [], []
with torch.no_grad():
    for xb, yb in test_loader:
        xb = xb.to(device)
        p = model(xb).cpu().numpy()
        preds.extend(p)
        trues.extend(yb.numpy())
preds = np.array(preds)
trues = np.array(trues)
rmse = np.sqrt(((preds - trues) ** 2).mean())
mae = np.abs(preds - trues).mean()
print(f"TEST RMSE {rmse:.4f} MAE {mae:.4f}")
print(f"OK -> {MODEL_FILE} best val {best_val:.5f}")

np.savez_compressed(NPZ_FILE, train_loss=np.array(hist_train), val_loss=np.array(hist_val), test_rmse=rmse, test_mae=mae, preds=preds, trues=trues)

with open(REPORTE_FILE, 'w', encoding='utf-8') as f:
    f.write(f"REPORTE 005 TRAIN\nEpochs {len(hist_train)}\nBest val {best_val:.5f}\nTest RMSE {rmse:.5f} MAE {mae:.5f}\nModel {MODEL_FILE}\n")

plt.figure()
plt.plot(hist_train, label='train')
plt.plot(hist_val, label='val')
plt.legend()
plt.title("Loss")
plt.savefig(RESULTS_DIR / "curvas_loss.png", dpi=150)
plt.close()

plt.figure()
plt.scatter(trues, preds, s=2, alpha=0.3)
plt.plot([0, 1], [0, 1], 'r--')
plt.xlabel("Real RUL")
plt.ylabel("Pred RUL")
plt.title(f"Pred vs Real RMSE {rmse:.3f}")
plt.savefig(RESULTS_DIR / "pred_vs_real.png", dpi=150)
plt.close()

MD_FILE.write_text(f"# 005_train\n\nTCN(3 bloques d=1,2,4) + Transformer 2 layers 4 heads\nTrain {len(train_idx)} Val {len(val_idx)} Test {len(test_idx)}\nBest val {best_val:.5f} RMSE {rmse:.5f}\n", encoding='utf-8')