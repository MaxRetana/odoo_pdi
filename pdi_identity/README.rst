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
* Interpreta una INE (frente y, opcionalmente, reverso) y valida la CURP (con
  su dígito verificador), la fecha de nacimiento, el sexo, la clave de elector
  y la vigencia. Cruza el frente con la zona de lectura mecánica del reverso y
  avisa de inconsistencias.
* Muestra los datos extraídos para que el usuario los revise y corrija antes
  de guardar.
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

Configuración
=============

#. Asigna a los usuarios el grupo **Escaneo de identificaciones / Usuario**.
   Sin él no se ve ningún botón ni los campos de la INE. Para escanear
   empleados se necesitan además permisos de RR. HH. (Oficial).
#. En *Ajustes > Identificaciones* se configura la ruta de Tesseract (solo si
   no está en el ``PATH``), el idioma del OCR (``spa`` por defecto) y si se
   conservan las imágenes (desactivado por defecto).

Uso
===

**Crear un contacto o empleado nuevo**

#. Abre la lista de Contactos (o de Empleados) y pulsa **Crear desde INE**.
#. Sube la foto del frente (y del reverso, si la tienes) y pulsa **Leer imagen**.
#. Revisa y corrige los datos. Las advertencias señalan lo que no se pudo
   validar.
#. Pulsa **Crear registro**.

**Completar un registro existente**

Abre el contacto o empleado y pulsa **Escanear INE**. Solo se escriben los datos
que se leyeron: lo que ya tenía el registro no se borra.

Privacidad
==========

Una INE contiene datos personales sensibles. El OCR se ejecuta en el servidor
de Odoo y las imágenes no se envían a servicios externos. Las imágenes no se
conservan al terminar, salvo que se active el ajuste correspondiente. Los
campos de la INE solo los ven los usuarios del grupo de escaneo.

Known issues / Roadmap
======================

* La precisión depende de la calidad de la foto: revisa siempre los datos.
* Solo se soporta la INE.
* No se lee el código QR ni el de barras del reverso.

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
