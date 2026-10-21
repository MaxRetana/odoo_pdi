# Escaneo de identificaciones (PDI)

Módulo de Odoo 19.0 que lee la imagen de un documento de identificación y extrae los datos básicos para crear o completar un registro sin teclear.

## Qué hace

- Preprocesa la imagen (orientación, contraste, escala) y ejecuta OCR con Tesseract, de forma local.
- Interpreta una **INE** (frente y reverso) y valida los datos: CURP, fecha de nacimiento, sexo, clave de elector y vigencia.
- Muestra los datos extraídos para que el usuario los revise antes de guardar.
- Crea o completa registros de `res.partner` (clientes y proveedores) y `hr.employee`.

## Estado

En desarrollo. Cada parte se entrega en su propio issue:

| Parte | Estado |
|-------|--------|
| Estructura del módulo | Listo |
| Preprocesamiento de imagen y OCR | Listo |
| Parser de INE | Listo |
| Asistente de escaneo | Listo |
| Integración con `res.partner` | Listo |
| Integración con `hr.employee` | Listo |

## Requisitos

- Odoo 19.0
- Tesseract OCR con el idioma español (`spa`)
- Paquetes de Python: `pytesseract`, `Pillow`

La instalación completa está en el [README de la raíz](../README.md).

## Estructura del módulo

```
pdi_identity/
├── __manifest__.py
├── models/       # campos y lógica de los modelos
├── wizard/       # asistente de escaneo
├── views/        # vistas y acciones
├── security/     # grupos y permisos
├── tools/        # preprocesamiento, OCR y parsers (Python puro)
├── tests/        # pruebas
├── data/         # datos del módulo
├── i18n/         # traducciones
└── static/description/
```

## Privacidad

Una INE contiene datos personales sensibles. El OCR se ejecuta en el servidor de Odoo y las imágenes no se envían a servicios externos. Las imágenes no se conservan una vez creado el registro, salvo que se configure lo contrario.

## Licencia

LGPL-3
