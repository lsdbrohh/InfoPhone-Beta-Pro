Guía de Instalación – Infophone

Requisitos

Antes de instalar, asegúrate de tener:

Python 3.10+ instalado en tu sistema (Windows recomendado).

pip actualizado:

Comando: python -m pip install --upgrade pip

Acceso a internet para descargar dependencias.

Instalación:

Clona el repositorio desde GitHub:

 Comando: git clone https://github.com/skeetlsd/infophone.git
cd infophone

Crear un entorno virtual (recomendado) para mas seguridad pero el creador no lo recomienda:

python -m venv venv

Activar el entorno virtual en windows el cual esta destinada esta herramienta:

venv\Scripts\activate

Linux / macOS:

Comando: source venv/bin/activate

Librerias:

pip install PyQt5

Las librerías estándar de Python (sys, os, time, json, subprocess, winreg, pathlib) no necesitan instalación.

Ejecucion: Ejecute una terminal sea en CMD o en mismo python y con CD si se acuerda de la ruta de la carpeta donde lo instalo copie y pegue la ruta pero si no se acuerda
En la carpeta arriba en la barra donde se puede customizar la URL ejecute el CMD desde ahi.  Una vez hecho use el comando python InfoPhone.py y se le ejecutara sin errores.


