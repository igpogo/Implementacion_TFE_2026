# Implementacion_TFE_2026
Sistema de protocolo de base de datos asíncrono diseñado para ejecutar operaciones CRUD y gestionar permisos utilizando el correo electrónico como canal de transporte. Esta solución permite operar en entornos de conectividad limitada o intermitente mediante mensajes cifrados y estructurados.

## Características Principales
- Protocolo Asíncrono sobre Email: Ejecución diferida y resiliente de instrucciones base de datos utilizando el correo como capa de red.
- Seguridad y Cifrado Simétrico: Protección end-to-end de payloads SQL y comandos de datos.
- Control de Acceso e Intercepción (auth_interceptor.py): Intercepción de mensajes entrantes para verificación de identidad y validación de permisos de usuario antes del procesamiento.
- Auditoría Completa (audit_logger.py): Registro detallado e inalterable de transacciones, ejecuciones y respuestas del sistema.
- Notificaciones por Lotes (batch_notifier.py): Agrupación eficiente de respuestas y notificaciones de estado para optimizar el tráfico de red.  Evaluación de Rendimiento Integrada: - Suite de mediciones de uso de CPU y memoria bajo cargas estresadas.
## 📂 Componentes del Sistema
### Módulos Núcleo (Sistema/)
- auth_interceptor.py: Intercepta los correos procesados, valida las firmas y credenciales, y aplica los controles de seguridad y políticas DevSecOps.  

- audit_logger.py: Captura logs transaccionales y eventos de seguridad para asegurar la trazabilidad del protocolo.  
- batch_notifier.py: Gestiona la cola de salida y empaqueta las respuestas en lotes hacia los usuarios receptores.  

### Métricas de Rendimiento (Sistema/Benchmarks_results/)
Contiene los archivos CSV resultantes de los benchmarks de consumo de recursos durante pruebas de estrés (de 1 a 1000 mensajes concurrentes):  
- benchmark_cpu*.csv / bm_cpu_*.csv: Muestreos de carga y tiempos de procesamiento de CPU.
- benchmark_memoria*.csv / bm_mem_*.csv: Consumo hídrico de memoria RAM durante la ejecución de lotes.  
### Manual de Usuario y Evidencias (Sistema/capturas_manual_usuario/)
Guía visual con la ejecución de flujos clave:  
- Alta y Creación Exitosa: Confirmación de registro e inserción de dato (01_ejemplo_alta_exitosa.png, 01_ejemplo_crear_exito.png).
- Lectura y Modificación: Demostración de consultas SQL y actualización (02_ejemplo_leer_exito.png, 03_ejemplo_modificar_exito.png).  
- Bloqueo de Seguridad: Intercepción de solicitud no autorizada (02_ejemplo_bloqueo_seguridad.png).  
##🛠️ Requisitos e Instalación
Requisitos Previos
- Python 3.13+
- SQLite 3
## Instalación
-Clonar el repositorio:
```bash
git clone https://github.com/igpogo/Implementacion_TFE_2026
cd Implementacion_TFE_2026
```
- Instalar dependencias necesarias:

```bash
pip install -r requirements.txt
```
-Ejecutar la suite de pruebas unitarias:

```bash
python -m unittest discover -s tests
```
