# Historial de cambios

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
