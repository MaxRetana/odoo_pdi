# Escaneo de identificaciones (PDI)

Módulo de Odoo 19.0 que lee la imagen de un documento de identificación y extrae los datos básicos para crear o completar un registro sin teclear.

## Qué hace

- Preprocesa la imagen (orientación, contraste, escala) y ejecuta OCR con Tesseract, de forma local.
- Interpreta una **INE** (frente y, opcionalmente, reverso) y valida los datos: CURP (con su dígito verificador), fecha de nacimiento, sexo, clave de elector y vigencia. Cruza el frente con la zona de lectura mecánica (MRZ) del reverso y avisa de inconsistencias.
- Muestra los datos extraídos para que el usuario los **revise y corrija** antes de guardar.
- Crea o completa registros de `res.partner` (clientes y proveedores) y `hr.employee`.

## Requisitos

- Odoo 19.0
- Tesseract OCR con el idioma español (`spa`)
- Paquetes de Python: `pytesseract`, `Pillow`

La instalación está en el [README de la raíz](../README.md).

## Configuración

1. **Permisos.** Asigna a los usuarios el grupo **Escaneo de identificaciones / Usuario** (los administradores lo tienen). Sin él no se ve ningún botón ni los campos de la INE. Para escanear empleados, el usuario necesita además permisos de RR. HH. (Oficial).
2. **Ajustes** (Ajustes → Identificaciones):
   - *Ruta de Tesseract*: solo si el binario no está en el `PATH` del servidor.
   - *Idioma del OCR*: `spa` por defecto; admite combinaciones como `spa+eng`.
   - *Conservar las imágenes*: por defecto desactivado (ver Privacidad).

## Uso

**Crear un contacto o empleado nuevo**

1. Ve a Contactos (o Empleados) → vista de lista → **Crear desde INE**.
2. Sube la foto del frente (y del reverso, si la tienes) → **Leer imagen**.
3. Revisa y corrige los datos. Las advertencias en amarillo señalan lo que el módulo no pudo validar.
4. **Crear registro**.

**Completar un registro existente**

Abre el contacto o empleado → **Escanear INE** → mismos pasos. Solo se escriben los datos que se leyeron: lo que ya tenía el registro no se borra.

### Qué se llena

| Dato de la INE | `res.partner` | `hr.employee` |
|----------------|---------------|---------------|
| Nombre completo | Nombre | Nombre |
| Domicilio | Calle, colonia, C.P., ciudad, estado, país | Domicilio privado |
| Fecha de nacimiento | — | Fecha de nacimiento |
| Sexo | — | Género |
| Estado de nacimiento | — | Lugar y país de nacimiento |
| CURP | Campo CURP | Número de identificación |
| Clave de elector | Campo propio | Campo propio |
| Vigencia | Campo propio | Campo propio |

## Estructura del módulo

```
pdi_identity/
├── __manifest__.py
├── models/       # mixin, servicio de OCR, res.partner, hr.employee, ajustes
├── wizard/       # asistente de escaneo (pdi.identity.scan)
├── views/        # vistas y acciones
├── security/     # grupo y permisos
├── tools/        # preprocesamiento, OCR, parser de INE y estados (Python puro)
├── tests/        # pruebas
├── i18n/         # plantilla .pot y es.po
└── static/description/
```

Las herramientas de `tools/` no dependen de Odoo y se pueden probar por separado. El motor de OCR está detrás de la interfaz `OcrEngine`: para usar otro, se sobrescribe `pdi.ocr.service._get_engine`.

## Pruebas

```bash
odoo-bin -d <base> -u pdi_identity --test-tags /pdi_identity --stop-after-init
```

Los textos de ejemplo de las pruebas son ficticios y simulan la salida del OCR, con y sin ruido.

## Privacidad

Una INE contiene datos personales sensibles.

- El OCR corre en el servidor de Odoo: las imágenes **no se envían a servicios externos**.
- Las imágenes **no se conservan** al terminar; solo se adjuntan al registro si activas *Conservar las imágenes*.
- Los campos CURP, clave de elector y vigencia solo los ven los usuarios del grupo de escaneo.
- Ningún dato personal se escribe en los registros de log.

## Límites conocidos

- La precisión depende de la calidad de la foto (nitidez, luz, reflejos, encuadre). **Revisa siempre los datos** antes de guardar.
- Solo se soporta la INE. Otros documentos (pasaporte, licencia) quedan para futuras versiones.
- Con solo dos líneas de nombre en el frente, el módulo toma la primera como apellido paterno y avisa para que se revise.
- No lee el código QR ni el de barras del reverso.
- Los términos de la interfaz están en español; `i18n/pdi_identity.pot` sirve como plantilla para otros idiomas.

## Licencia

LGPL-3
