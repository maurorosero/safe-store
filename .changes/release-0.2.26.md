## [0.2.26] - 2026-11-27

- El README describia un producto que ya no existe: pedia pegar la master key a mano, mandaba al Ingress del add-on, afirmaba que /data entero queda fuera del backup (solo se excluye master.key) y decia que el panel no distingue administradores. Se reescribe con el flujo real (imagen publicada, llave generada en /data/master.key, panel del componente solo para admin) y se agrega arriba la advertencia de que el shim hookea un metodo privado y puede romperse con una actualizacion de HA.
- _data_to_save parte de super() y solo transforma el data, asi que los campos que agregue el core no se pierden; el fragmento opaco de orjson se convierte antes de tocarlo; si una entrada no se puede cifrar se aborta el guardado en vez de escribirla en claro; _clave_local se elimina, sin add-on no hay clave nueva; las recargas del puente van de a una y solo para las entradas afectadas.

