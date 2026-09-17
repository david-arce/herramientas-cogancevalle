# Presupuesto de nómina: tabla única con recálculo automático

## Resumen

| Antes | Ahora |
|---|---|
| 34 tablas (una definitiva y una auxiliar por concepto) | 1 tabla: `presupuesto_nomina`, con columna `tipo` |
| `conceptos_fijos_y_variables` + `concepto_auxilio_educacion` | 1 tabla: `conceptos_nomina`, con columna `anio`; se llena subiendo un Excel |
| Editar en la auxiliar → "Subir presupuesto" | Se edita y se guarda directo |
| ~150 vistas y 36 templates | `views_nomina.py` y un solo template para todos los conceptos |
| Cálculos en el navegador | Cálculos en el servidor (`nomina_motor.py`), en cascada |
| Distribución dentro de cada concepto | Distribución por persona, una sola vez, en la vista consolidada |

## Cómo funciona

### Origen de cada fila

- **⚙️ Calculado**: lo calcula el sistema y se actualiza cada vez que cambia algo de lo que depende.
- **✋ Manual**: alguien la editó o la agregó; el sistema la respeta.
- **⚙️ Restablecer cálculo en seleccionadas**: devuelve filas manuales al cálculo automático.

### Cascada

```
Sueldos, Comisiones, Horas extra, Medios de transporte, Aprendices
   ├─> Auxilio de transporte ─┐
   ├──────────────────────────┴─> Cesantías ─> Intereses de cesantías
   │                           └─> Prima
   └─> Vacaciones, Bonificaciones, Bonificaciones foco, Seguridad social
```

- **Al guardar, cargar o borrar un concepto** se recalculan todos los que dependen de él.
- **Al guardar parámetros**, o con "🔄 Recalcular todo", se recalcula el presupuesto completo.

### Qué se actualiza con una fila manual

**➕ Agregar fila** abre un diálogo con los conceptos que dependen del actual, todos marcados. En sueldos son auxilio de transporte, cesantías, prima, vacaciones, intereses de cesantías, bonificaciones, bonificaciones foco y seguridad social.

- **Al desmarcar**: la fila no se tiene en cuenta en ese concepto (campo `excluir_de`). La exclusión se hereda por la cadena: sin cesantías tampoco hay intereses.
- **Cambiarlo después**: con el botón 🔗 de las filas manuales, que se ve resaltado cuando la fila tiene exclusiones.
- **En Excel**: la exportación muestra la columna `no_actualiza`.

### Cuenta contable

Cada NOMCOSTO corresponde a una cuenta, y en `presupuesto_nomina` el NOMCOSTO es el campo `area`. Por eso la cuenta depende solo del área:

- **Origen**: se toma de `conceptos_nomina` (año base). Si un NOMCOSTO aparece con varias cuentas, se usa la más frecuente. El área se compara sin importar mayúsculas, tildes ni espacios.
- **Cuándo se asigna**: a toda fila cargada, calculada, distribuida, creada a mano o a la que se le cambia el área.
- **Área que no existe en los datos**: la fila queda sin cuenta. "Agregar NOMCOSTO" en el tablero pide la cuenta, y las filas con esa área la reciben al instante.
- **Recalcular todo**: vuelve a poner a cada fila la cuenta de su área.
- **Visibilidad**: no se muestra en las tablas; sí sale en la exportación a Excel y en la lista de NOMCOSTO del tablero.

### Distribución por persona (vista consolidada)

En **Ver todo consolidado → Distribución por persona**:

1. Marque cualquier fila de cada persona, o búsquela por nombre o cédula.
2. Escriba los porcentajes por destino (deben sumar 100 %). Con "➕ Otro destino" puede elegir cualquier centro y área.
3. Pulse **Aplicar distribución**.

Qué pasa al aplicar:

- **Alcance**: se reparten todas las filas de la persona en todos los conceptos base. Las calculadas guardan su porcentaje y siguen recalculándose; las manuales reparten sus valores. Las copias conservan sus exclusiones y toman la cuenta de su nueva área.
- **Derivados**: se recalculan con el nuevo reparto. Los ajustes manuales de conceptos calculados de esa persona se descartan.
- **Persistencia**: la distribución se guarda en `distribucion_nomina` y se vuelve a aplicar sola al recargar desde Conceptos o subir un Excel.
- **Editar / Quitar**: "Editar" carga el reparto en el formulario; "Quitar" devuelve a la persona a su centro y área de origen.

### Seguridad social

- **Técnicos**: en `ASISTENCIA TECNICA PROPIA` y `ASISTENCIA TECNICA CONVENIO` se calcula por persona (cédula, nombre, cargo, centro y área). La lista está en `AREAS_POR_PERSONA`.
- **Resto de áreas**: se consolida por centro y área.
- **Aftosa**: `PROYECTO AFTOSA GASTOS DE PERSONAL` se consolida sin centro.
- **Reglas conservadas**: tope de 10 SMMLV, cédula especial, salud de aprendices 12,5 % y ARL por centro/área.

## Datos de origen (tablero → "Datos de origen")

La sección se puede ocultar, y la página recuerda si quedó oculta.

- **Año base**: los conceptos se leen de ese año y el auxilio de educación del año anterior. Por defecto es el año más reciente cargado; se puede fijar.
- **Meses reales**: cuántos meses (desde enero) tienen datos reales. Se toma, en orden:
  1. el valor fijado en el tablero;
  2. la fecha de corte indicada al subir el archivo;
  3. el último mes con valores.
  
  Con datos hasta agosto, comisiones incrementa enero–agosto y proyecta el resto con el promedio. Horas extra y bolsa de consumibles descartan el último mes real, como el cálculo original (`'descartar'` en el catálogo).
- **Subir Excel**:
  - **Columnas**: obligatorias `CEDULA` y `CONCEPTO`, más los meses o `CONCEPTO_F`. Acepta variantes (`Cédula`, `Setiembre`, `Nombre Cen`), títulos encima del encabezado, CSV con coma o punto y coma, y `.xls` (requiere `pip install xlrd`).
  - **Año**: indique el año. Si el archivo trae columna `AÑO` o `FECHA`, esa tiene prioridad.
  - **Reemplazo**: los datos de ese año **siempre se reemplazan**.
  - **Códigos**: se completan con ceros (`1` → `001`).
  - **Recargar**: la casilla "Recargar el presupuesto" vuelve a cargar todos los conceptos base y recalcula.
- **Recargar desde Conceptos** reemplaza las filas de los conceptos base, incluidas las manuales. Los ajustes manuales de conceptos calculados y las distribuciones se conservan.

## Instalación

Haga primero una copia de la base de datos.

### Si ya aplicó una versión anterior

```bash
python nomina_tabla_unica/actualizar_conceptos.py presupuestoApp --simular
python nomina_tabla_unica/actualizar_conceptos.py presupuestoApp
python manage.py makemigrations presupuestoApp
python manage.py migrate
```

El script copia los módulos, templates y estáticos que cambiaron, y deja un `.bak` de cada uno. Después suba el Excel en el tablero (con "Recargar el presupuesto" marcado) o pulse "🔄 Recalcular todo".

### Instalación nueva

1. `python aplicar_cambios.py presupuestoApp` (con `--simular` primero). El script:
   - mueve las 34 clases viejas a `models_nomina_legado.py`;
   - limpia `views.py`;
   - copia lo nuevo;
   - avisa qué rutas de `urls.py` quedaron rotas.
2. En `urls.py`, borre las rutas viejas de nómina y ponga al inicio de `urlpatterns` (antes de las rutas `<str:area>/`):
   ```python
   from .urls_nomina import urlpatterns as urls_nomina
   urlpatterns = [
       *urls_nomina,
       ...
   ]
   ```
3. `python manage.py makemigrations` y `python manage.py migrate`.
4. Suba el Excel de conceptos desde `nomina/`.
5. Opcional:
   - `migrar_nomina_tabla_unica` copia el presupuesto guardado en las 34 tablas viejas.
   - `migrar_conceptos_nomina --anio AAAA` copia las dos tablas viejas de conceptos.
   
   No son necesarios si va a trabajar con datos nuevos.
6. Cuando todo esté bien, puede quitar de `models.py`:
   - `models_nomina_legado`: con `makemigrations`/`migrate` se borran las 34 tablas.
   - `ConceptosFijosYVariables` y `ConceptoAuxilioEducacion`: son `managed = False`, así que sus tablas se borran a mano.

## Archivos

```
aplicar_cambios.py              integración inicial
actualizar_conceptos.py         actualiza una instalación existente
app/models_nomina.py            PresupuestoNomina, ConceptosNomina, ConfiguracionNomina, DistribucionNomina
app/nomina_motor.py             catálogo, fórmulas, cascada, distribución, cuentas, seguridad social
app/nomina_conceptos.py         datos de origen: año base, meses reales, importación de Excel
app/views_nomina.py             vistas
app/urls_nomina.py              rutas
app/management/commands/        migrar_nomina_tabla_unica, migrar_conceptos_nomina
app/templates/presupuesto_nomina/
    dashboard_nomina.html       tablero, datos de origen, parámetros, altas
    tabla_concepto.html         pantalla de cualquier concepto y del consolidado
    _panel_distribucion.html    distribución por persona (consolidado)
    _dialogo_actualiza.html     "qué se actualiza con esta fila"
    base_tabla.html
app/static/js/                  presupuesto_tabla.js, presupuesto_nomina.js, presupuesto_distribucion.js
app/static/css/                 presupuesto_tabla.css
```

## Para revisar con el negocio

- **Fórmulas reconstruidas**: `presupuesto_calculos.js` no venía en el archivo original, así que las fórmulas se reconstruyeron. Están juntas en `nomina_motor.py` (sección "Fórmulas").
- **Código E14 compartido**: bolsa de consumibles y auxilio TBC/KIT cargan ambos el concepto `E14`.
- **Valores fijos en el código**: 200.000 (auxilio de transporte) y 220.000 (bonificación foco). Podrían pasar a parámetros.
