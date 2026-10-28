===================================
Escaneo de identificaciones (PDI)
===================================

Lee la imagen de un documento de identificación y extrae los datos básicos
para crear o completar un registro sin teclear.

**Table of contents**

.. contents::
   :local:

Funcionalidad
=============

* Preprocesa la imagen (orientación, contraste, escala) y ejecuta OCR con
  Tesseract, de forma local.
* Interpreta una INE (frente y reverso) y valida CURP, fecha de nacimiento,
  sexo, clave de elector y vigencia.
* Muestra los datos extraídos para que el usuario los revise antes de guardar.
* Crea o completa registros de ``res.partner`` (clientes y proveedores) y de
  ``hr.employee``.

Instalación
===========

Requisitos externos:

* Tesseract OCR con el idioma español (``spa``).
* Paquetes de Python ``pytesseract`` y ``Pillow``.

En Debian o Ubuntu::

    sudo apt install tesseract-ocr tesseract-ocr-spa
    pip install pytesseract Pillow

Privacidad
==========

Una INE contiene datos personales sensibles. El OCR se ejecuta en el servidor
de Odoo y las imágenes no se envían a servicios externos. Las imágenes no se
conservan una vez creado el registro, salvo que se configure lo contrario.

Bug Tracker
===========

Los errores se reportan en
`GitHub Issues <https://github.com/MaxRetana/odoo_pdi/issues>`_.

Credits
=======

Authors
~~~~~~~

* MaxRetana

Maintainers
~~~~~~~~~~~

Este módulo es mantenido por MaxRetana.
