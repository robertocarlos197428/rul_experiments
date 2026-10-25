creacion de database MASTER_RUL de bibliografia de rul

extracion de datos bibliograficos
se consultaron 14 papers de review desde 2018 a 2026 (10 pdf y 3 bib) y se extrajeron las referecias bibliograficas de cada uno.
las referencias se pasaron a txt desde pdf
inicialmente los campos obtenidos para la creacion del master fueron los siguientes
author;title;year;journal;publisher;doi;url;editor;source_file
con los txt y bib se contruyeron 14 archivos .csv con este nombre: REVIEW_AÑO_AUTOR_CANT.csv donde CANT corresponde a la cantidad de datos bibliograficos encontrados en cada paper

consolidación por año:
se consolidaron en archivos por año obteniendose 4 archivos REVIEW_2026.csv, REVIEW_2025.csv, REVIEW_2024_2023.csv, REVIEW_2018_YAGUO_374.csv (era el unico archivo base de 2018)
en esta etapa se agrego el campo N_source_file que corresponde al numero correlativo del dato bibliografico en su archivo de origen
se extrajeron los doi de los archivos que lo traian como link y no el doi directo y se completaron los consolidados, para cada archivo se creo su propio .py
de los consolidados se puede apreciar que hay inconcordancia en los formatos de los nombres de autor, además las columnas publisher y editor no aportan datos relevantes y se eliminan, además los archivos han sido revisados y mdoficados en excel por lo cual no cuentan con el formato oficial csv ya que quedan separados por punto y coma
campos seleccionados
author;title;year;journal;doi;url;source_file;N_source_file

creacion MASTER_RAW_V1
a partir de los 4 csv se crea el MASTER_RAW_V1
cuenta con encabezado: author;title;year;journal;doi;url;source_file;N_source_file
y 2209 archivos bibliograficos, se debe normalizar nombres
se normalizan nombres se decide dejar el delimitador en ;
se queda MASTER_RAW.csv



