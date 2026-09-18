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

### Conceptos base y conceptos calculados

- **Base** (sueldos, comisiones, horas extra, medios de transporte, ayuda de transporte, bolsa de consumibles, TBC/KIT, educación, aprendices, bonos Kyrovet): se cargan desde Conceptos y se pueden editar.
  - **⚙️ Calculado**: la fila viene del Excel y se actualiza sola con los parámetros.
  - **✋ Manual**: alguien la editó o la agregó; el sistema la respeta.
  - **⚙️ Restablecer cálculo en seleccionadas**: devuelve filas manuales al cálculo automático.
- **Calculados** (auxilio de transporte, cesantías, prima, vacaciones, intereses de cesantías, bonificaciones, bonificaciones foco, seguridad social): **siempre** los hace el sistema. Su tabla es de solo lectura y se rehace completa en cada recálculo; no guardan filas manuales.
  - Para cambiar sus valores, edite el concepto de origen o los parámetros.
  - Para que una persona no entre en alguno, use el diálogo "qué se actualiza" en la fila de origen.
  - El botón **🔄 Recalcular** de esas pantallas los vuelve a hacer con los datos de hoy.

### Cascada

```
Sueldos, Comisiones, Horas extra, Medios de transporte, Aprendices
   ├─> Auxilio de transporte ─┐
   ├──────────────────────────┴─> Cesantías ─> Intereses de cesantías
   │                           └─> Prima
   └─> Vacaciones, Bonificaciones, Bonificaciones foco, Seguridad social
```

- **Al guardar, cargar o borrar un concepto base** se recalculan todos los que dependen de él.
- **Al guardar parámetros**, o con "🔄 Recalcular todo", se recalcula el presupuesto completo.

### Qué se actualiza con una fila manual

**➕ Agregar fila** abre un diálogo con los conceptos que dependen del actual, todos marcados. En sueldos son auxilio de transporte, cesantías, prima, vacaciones, intereses de cesantías, bonificaciones, bonificaciones foco y seguridad social.

- **Al desmarcar**: la fila no se tiene en cuenta en ese concepto (campo `excluir_de`). La exclusión se hereda por la cadena: sin cesantías tampoco hay intereses.
- **Cambiarlo después**: con el botón 🔗 de las filas manuales, que se ve resaltado cuando la fila tiene exclusiones.
- **En Excel**: la exportación muestra la columna `no_actualiza`.

### Intereses de cesantías

Se calculan sobre las cesantías acumuladas, mes a mes:

```
interés del mes = cesantías acumuladas × (30 × meses) × % / 360 − intereses de los meses anteriores
```

- **Primer mes**: 30 días. El segundo: 60. Y así sucesivamente.
- **Ingreso después de enero**: los días se cuentan desde el primer mes con cesantías. Quien entra en marzo tiene 30 días en marzo, 60 en abril, etc.
- **Varios periodos en el año**: un mes sin cesantías corta el periodo. No causa intereses y el siguiente periodo vuelve a empezar en 30 días, con el acumulado en cero. Ejemplo: cesantías en mayo y junio y otra vez en noviembre y diciembre → los intereses de noviembre y diciembre son iguales a los de mayo y junio.
- **Año completo**: el total del año queda en el 12 % de las cesantías acumuladas, como en la liquidación anual.
- **Ejemplo**: con cesantías de 355.514 en enero y febrero y 456.835 en marzo, al 12 % da 3.555, 10.665 y 20.815.
- El porcentaje es el parámetro "Intereses cesantías (%)", **escrito como porcentaje**: 12 son 12 %. Si se escribe 1, los intereses salen doce veces más bajos. El tablero avisa cuando un porcentaje queda fuera de lo habitual.

### Edición tipo Excel

En las tablas de los conceptos base:

- **Moverse**: flechas, `Tab`, `Inicio`/`Fin`, `RePág`/`AvPág`. `Enter` o `F2` abren la celda; dentro de la celda, `Enter` guarda, **sale del modo edición** y baja (`Shift+Enter` sube). `Tab` guarda y abre la celda siguiente.
- **Flechas mientras se edita**: si el valor se acaba de escribir, las flechas guardan y cambian de celda. Si entró con doble clic para corregir un texto, mueven el cursor dentro del texto y salen de la celda al llegar al borde.
- **Escribir**: teclear sobre una celda reemplaza su contenido. En las columnas con lista, la letra escrita busca la opción.
- **Seleccionar**: `Shift`+flechas, `Shift`+clic, o arrastrar con el mouse.
- **Copiar y pegar**: `Ctrl+C`, `Ctrl+X` y `Ctrl+V`, en formato TSV, así que funciona contra Excel en los dos sentidos. Si se pegan más líneas que filas, se agregan filas nuevas.
- **Borrar**: `Supr` vacía el rango seleccionado.
- **Rellenar**: arrastrar el cuadrito azul de la esquina copia los valores; doble clic sobre él llena hasta la última fila.

Al **agregar una fila**, el concepto se pone solo (el más usado en esa pantalla), la tabla baja hasta ella, la resalta y deja el cursor en su primera celda. Si algún filtro la escondía, se limpian los filtros.

### Bonificación foco

Se calcula en enero, con dos fórmulas según la persona.

**Quien comisiona** (tiene filas en Comisiones y no está en la lista de excepciones):

1. Se toman sus comisiones **reales** del año base, de `conceptos_nomina` (concepto 389), no las presupuestadas.
2. El promedio de lo real se saca **solo con los meses que tienen valor**: quien comisionó de junio a septiembre se divide entre 4, no entre 9.
3. Los meses que aún no tienen dato real (según "Meses con datos reales") se llenan con ese promedio.
4. Se suman los 12 meses y se divide entre 12, aunque solo haya valores en dos o tres meses.
5. Ese promedio es la bonificación. **No se le aplica ningún incremento**: el IPC es solo para quienes no comisionan.

**Quien no comisiona**, y quien esté en la lista de excepciones (estos sí llevan IPC):

1. **Base**: el valor de enero de la bonificación foco de alguien que no comisiona y trabajó el año completo. Se busca en `conceptos_nomina` el concepto cuyo nombre contiene "FOCO"; si no está en los datos, se usa 220.000. A la base se le aplica el IPC.
2. **Días trabajados**: desde la fecha de ingreso (`FECHAINGRE`) hasta el 30 de diciembre, con meses de 30 días. Quien ingresó antes del año base cuenta 360.
3. **Valor** = base ÷ 360 × días. Ejemplos: ingreso el 1 de julio → medio valor; el 16 de septiembre → 105 días.

**Agregar personas a mano**: la pantalla de Bonificaciones foco tiene **➕ Agregar fila** y **💾 Guardar**, para quien el cálculo no cubre (por ejemplo, alguien que no comisionó y entró en el mes del presupuesto). Esas filas quedan como ✋ Manual, no se calculan y sobreviven a los recálculos; si coinciden con una persona calculada, reemplazan su fila. Los cambios sobre las filas ⚙️ Calculadas no se guardan y el mensaje lo indica. Es el único concepto calculado que admite filas a mano.

**Lista de excepciones**: en el tablero, sección "Bonificación foco", aparecen las personas con comisiones. Al marcar a alguien, se le calcula como si no comisionara (incluso si su cargo es comercial) y la bonificación se recalcula al guardar.

### Cuenta contable

Cada NOMCOSTO corresponde a una cuenta, y en `presupuesto_nomina` el NOMCOSTO es el campo `area`. Por eso la cuenta depende solo del área:

- **Al subir el Excel**: la columna `CUENTA` se guarda tal cual (sin el `.0` que agrega Excel). Las filas que no traen cuenta la toman de su NOMCOSTO, primero del mismo archivo y si no de los datos ya cargados. Si el archivo no trae la columna, todas se completan así. Después, las filas del presupuesto se actualizan con la cuenta de su área, aunque no se marque "Recargar". El panel de años muestra cuántas filas quedaron sin cuenta.
- **Origen**: se toma de `conceptos_nomina` (año base). Si un NOMCOSTO aparece con varias cuentas, se usa la más frecuente. El área se compara sin importar mayúsculas, tildes ni espacios.
- **Cuándo se asigna**: a toda fila cargada, calculada, distribuida, creada a mano o a la que se le cambia el área.
- **Fecha de ingreso**: la columna `FECHAINGRE` se guarda en `conceptos_nomina.fecha_ingreso`. Excel la entrega como número de serie (44167 = 02/12/2020) y también se aceptan fechas escritas (15/03/2019) o celdas con formato de fecha. Se reconocen los encabezados `FECHAINGRE`, `FECHA DE INGRESO`, `FECHA_INGRESO` e `INGRESO`. El panel de años muestra cuántas filas la traen, y sale en la plantilla y en la exportación.

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
- **Derivados**: se recalculan con el nuevo reparto.
- **Persistencia**: la distribución se guarda en `distribucion_nomina` y se vuelve a aplicar sola al recargar desde Conceptos o subir un Excel.
- **Editar / Quitar**: "Editar" carga el reparto en el formulario; "Quitar" devuelve a la persona a su centro y área de origen.

### Seguridad social

- **Técnicos**: en `ASISTENCIA TECNICA PROPIA` y `ASISTENCIA TECNICA CONVENIO` se calcula por persona (cédula, nombre, cargo, centro y área). La lista está en `AREAS_POR_PERSONA`.
- **Filas viejas**: cualquier fila de seguridad social copiada de las tablas anteriores desaparece en el primer recálculo, porque el concepto se rehace completo.
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
  - **Columnas**: obligatorias `CEDULA` y `CONCEPTO`, más los meses o `CONCEPTO_F`. También se guarda `FECHAINGRE` (fecha de ingreso). Acepta variantes (`Cédula`, `Setiembre`, `Nombre Cen`), títulos encima del encabezado, CSV con coma o punto y coma, y `.xls` (requiere `pip install xlrd`).
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
   - `migrar_nomina_tabla_unica` copia el presupuesto guardado en las 34 tablas viejas (solo los conceptos base: los calculados los rehace el motor).
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
