## [0.2.24] - 2026-11-27

- La restauracion escribia la llave en options.json, y las opciones si viajan en el backup: la llave terminaba copiada en cada backup. Ahora se escribe en /data/master.key con 600, se verifica que quedo, y recien despues se vacia la opcion. Al arrancar, una clave que haya llegado por las opciones se mueve al archivo. Cuatro pruebas con un directorio real.

