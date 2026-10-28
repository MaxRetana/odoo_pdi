# odoo_pdi

Módulo de Odoo para procesamiento digital de imágenes (PDI). Al cargar la imagen de un documento de identificación se extraen los datos básicos para crear el registro sin teclearlos.

- **Versión de Odoo:** 19.0
- **Documentos soportados:** INE (frente y reverso)
- **Modelos:** `res.partner` (clientes y proveedores) y `hr.employee`
- **OCR:** Tesseract, de forma local (los datos de una identificación no salen del servidor)

## Estructura del repositorio

```
.
├── .gitignore
├── README.md          # este archivo
└── pdi_identity/      # módulo de Odoo
    ├── README.md      # documentación del módulo (Git)
    └── README.rst     # documentación del módulo (Odoo)
```

## Requisitos

- Odoo 19.0
- Python 3.10 o superior
- Tesseract OCR con el paquete de idioma español (`spa`)
- Paquetes de Python: `pytesseract` y `Pillow`

## Instalación

1. Instalar Tesseract y el idioma español:

   ```bash
   # Debian / Ubuntu
   sudo apt install tesseract-ocr tesseract-ocr-spa
   # macOS
   brew install tesseract tesseract-lang
   ```

2. Instalar las dependencias de Python en el entorno de Odoo:

   ```bash
   pip install pytesseract Pillow
   ```

3. Agregar la raíz de este repo a `addons_path` en `odoo.conf`.
4. Actualizar la lista de aplicaciones e instalar **Escaneo de identificaciones (PDI)**.

## Flujo de ramas

```
rama de issue ──PR──▶ develop ──automático──▶ test ──PR──▶ main
```

Cada cambio nace de un issue, en una rama desde `develop`, y entra por Pull Request. `develop`, `test` y `main` están protegidas: no se hace push directo.

## Licencia

LGPL-3
