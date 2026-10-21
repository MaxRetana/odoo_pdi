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

## Contribuir

1. Todo cambio parte de un issue. Crea el issue con la plantilla que corresponda (bug, funcionalidad, tarea, historia o epic) y asígnalo a un proyecto.
2. Crea una rama desde `develop` con el prefijo del tipo de cambio: `feat/`, `fix/`, `chore/`, `ci/` o `docs/`, y el número del issue (por ejemplo `feat/12-integracion-hr-employee`).
3. Haz commits pequeños y abre un Pull Request **hacia `develop`**, con `Closes #N` en la descripción y siguiendo la plantilla del PR.
4. Corre las pruebas antes de abrirlo (ver el [README del módulo](pdi_identity/README.md#pruebas)).
5. Al mergear a `develop`, un workflow lo pasa a `test` y mantiene abierto un PR `test → main`, que se mergea manualmente.

## Licencia

LGPL-3
