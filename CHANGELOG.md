# Historial de cambios

## Sin publicar

- **Distribucion**: el proyecto se puede instalar con `pipx install imagenes`
  (`pyproject.toml`) y cada etiqueta `vX.Y.Z` publica una Release de GitHub con
  el `imagenes.exe` de Windows ya compilado y los paquetes para PyPI.
- Integracion continua: las pruebas corren en Linux y Windows con Python
  3.10-3.13.
- README en ingles y espanol.

## 2.1.0 - 2026-08-31

Tres fallos encontrados midiendo, no mirando, mas robustez y filtros.

### Fallos corregidos

- **Ctrl+C no paraba nada.** El pool de hilos esperaba a toda la cola al salir.
  Medido con 168 trabajos: antes se procesaban los 168 y tardaba 5,2 s en
  devolver el control; ahora se paran en 10 y tarda 0,8 s. Se informa de lo que
  dio tiempo a hacer y se sale con codigo 130.
- **La memoria no tenia techo.** Medido: 2,6 GB con 112 fotos de 12 Mpx, y
  9,5 GB con 8 panoramicas de 100 Mpx. Dos frenos que salen de medir:
  un presupuesto de bytes descomprimidos en vuelo (las panoramicas bajan de
  9,5 GB a 1,2 GB) y un tope de codificaciones AVIF simultaneas, que cuestan
  unos 390 MB cada una y por encima de 4 no dan ni un segundo de mejora
  (62 s con 4 hilos, 66 s con 8). El caso normal pasa de 2.580 a 1.982 MB con
  el mismo tiempo.
- **Rutas de mas de 260 caracteres.** Al replicar el arbol de carpetas, la
  salida se alargo y en Windows fallaba todo con un enganoso `No such file or
  directory`. Ahora se prefijan las rutas y el error dice lo que pasa de
  verdad. De paso aparecio algo peor: `os.walk` sobre una carpeta honda no
  entra y devuelve una lista vacia **sin dar error**, asi que esas imagenes se
  saltaban en silencio.
- **`collect_inputs` pisaba su propio parametro.** La variable de la carpeta
  excluida se llamaba igual que la de los patrones de exclusion.
- El epilogo de `--help` salia roto: `C:otos` se interpretaba como un salto
  de pagina.

### Novedades

- **Escritura atomica**: se escribe a un `.tmp` y se renombra al final. Un
  corte a media escritura deja un `.tmp`, no un archivo con el nombre bueno y
  el contenido roto.
- **`errores.log`** junto al informe: cerrar la ventana ya no se lleva por
  delante la lista de lo que fallo.
- **Los avisos salen segun ocurren**, no todos al terminar.
- **`--vigilar [SEGUNDOS]`**: deja la carpeta abierta y convierte lo que vaya
  llegando. No toca un archivo hasta que deja de crecer, para no convertir una
  foto a medio copiar.
- **`--originales dejar|mover|borrar`**: aparta o borra el original, pero solo
  si la conversion salio sin un solo error y se escribio algo.
- **`--excluir PATRON`**, repetible: `borradores/*`, `*.tmp.*`.
- **`--min-px N`**: se salta iconos y firmas.
- **`--no-recomprimir`**: no rehace lo que ya esta en ese formato y cabe en la
  medida, para no perder calidad por recomprimir.
- El asistente pregunta por todo lo anterior en las opciones avanzadas, y
  pide confirmacion antes de borrar originales.
- **76 pruebas**, incluidas las primeras del asistente.

## 2.0.0 - 2026-08-29

Reescritura del motor. El codigo pasa de un solo archivo a un paquete con
pruebas automaticas.

### Fallos corregidos

- **Se perdian imagenes sin avisar.** La salida era plana aunque la busqueda
  fuera recursiva: dos `foto.jpg` en subcarpetas distintas escribian el mismo
  `foto.webp` y la segunda borraba a la primera, contando las dos como
  convertidas. Ahora se replica el arbol de carpetas de origen.
- **Colision entre extensiones.** `foto.png` y `foto.jpg` en la misma carpeta
  daban los dos `foto.webp`. Ahora el segundo sale como `foto-2.webp`.
- **Se perdia el perfil de color.** No se pasaba `icc_profile` al guardar, asi
  que cualquier foto en AdobeRGB o Display P3 salia visiblemente desaturada.
- **Se perdia la animacion de los GIF**, en silencio y sin aviso.
- **La exclusion de la carpeta de salida era por prefijo de cadena**, asi que
  una carpeta llamada `imagenes_convertidas_old` quedaba excluida por error.
- **Ficheros sin cerrar**: `Image.open()` sin `with` dejaba handles abiertos.
- **`overwrite` era codigo muerto**: estaba fijado a `True` y no se preguntaba.
- **El orden natural solo miraba el nombre**, no la ruta: en modo recursivo las
  carpetas se entremezclaban.
- **El contador SEO no rellenaba con ceros**: `-1, -10, -100` ordenaba mal.
- **`reporte.csv` se sobrescribia** en cada tanda.

Y uno introducido durante esta misma reescritura, encontrado al comparar la
salida contra la version 1 con fotos reales:

- **Los JPEG de iPhone salian tumbados.** Son ficheros MPO: llevan una segunda
  imagen incrustada y declaran `n_frames = 2`. El detector de animaciones los
  daba por animados, y esa rama se saltaba la rotacion EXIF y el perfil de
  color. Ahora la deteccion mira tambien el formato del fichero.

### Novedades

- Conversion en paralelo con hilos: medido 4,5x mas rapido con 8 hilos.
- Formatos AVIF (35% mas ligero que WEBP) y lectura de HEIC/HEIF.
- Modo directo por linea de ordenes, con `--simular` para ver antes de hacer.
- Presets (`web`, `woo`, `rapido`, `maxima-calidad`) y presets propios.
- Recuerda la ultima configuracion usada.
- Se puede arrastrar una carpeta sobre el ejecutable.
- Menu contextual de Windows y "Enviar a".
- Modos de encaje `ajustar`, `recortar` y `rellenar`.
- Control de metadatos EXIF: `limpiar` quita la ubicacion GPS.
- Control de perfil de color: conservarlo o convertir a sRGB.
- Barra de progreso con tiempo restante.
- Informe CSV con el ahorro real, y `snippet.html` con `<picture>`/`srcset`.
- `INSTALAR.bat`, que faltaba en el paquete.
- `--diagnostico`, que dice que formatos y funciones hay disponibles.
- El modo directo es determinista: no arrastra la configuracion de la vez
  anterior, para que un comando en un script haga siempre lo mismo.
- 45 pruebas automaticas.

## 1.0.0

Version inicial: asistente por terminal, WEBP/JPG/PNG/BMP/TIFF, tamanos fijos
y nombres SEO.
