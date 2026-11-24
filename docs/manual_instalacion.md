# Manual de instalación del tablero y la API

Este manual explica cómo desplegar la **API del modelo** (FastAPI, puerto 8001) y el **tablero** (Dash, puerto 8050) con Docker Compose, en una instancia AWS EC2 o en un computador local. El uso del tablero está en el [manual de usuario](manual_usuario.md).

## 1. Componentes

| Componente | Carpeta | Imagen Docker | Puerto |
|---|---|---|---|
| API del modelo | `api/` (usa `models/`, `src/modelado.py` y `tablero/datos/`) | `api-rendimiento` | 8001 |
| Tablero | `tablero/` | `tablero-rendimiento` | 8050 |
| Orquestación | `docker-compose.yml` | — | — |

El tablero se comunica con la API por la variable `API_URL`, que `docker-compose.yml` fija en `http://api:8001`. El tablero arranca solo cuando la API responde `/health`.

**Requisitos:**
- Docker 24 o superior con el plugin Compose v2 (`docker compose`).
- Git.
- 2 GB de RAM (en EC2, `t3.small` o superior; con `t2.micro` hay que agregar swap, ver 2.3).
- Acceso a internet para descargar las imágenes base y los paquetes de Python.

## 2. Despliegue en AWS EC2

### 2.1 Preparar la instancia (consola de AWS)

1. **Lanzar o encender la instancia.** EC2 → *Instances*. Ubuntu Server 22.04 o 24.04 LTS, tipo `t3.small` o superior. Si ya existe, *Instance state* → **Start**.
2. **Anotar la IP.** Copie la **Public IPv4 address**. Cambia cada vez que la instancia se detiene, salvo que tenga una Elastic IP.
3. **Abrir los puertos.** Pestaña *Security* → *Security group* → **Edit inbound rules**. Agregue reglas *Custom TCP*:

| Puerto | Uso | Origen |
|---|---|---|
| 22 | SSH | Su IP |
| 8001 | API | 0.0.0.0/0 |
| 8050 | Tablero | 0.0.0.0/0 |
| 5000 | MLflow (opcional) | 0.0.0.0/0 |

### 2.2 Conectarse por SSH

Desde macOS o Linux:

```bash
chmod 400 ~/Downloads/<llave>.pem
ssh -i ~/Downloads/<llave>.pem ubuntu@<IP-PUBLICA>
```

En Windows se puede usar PowerShell (`ssh -i C:\ruta\<llave>.pem ubuntu@<IP-PUBLICA>`) o *EC2 Instance Connect* desde la consola.

### 2.3 Instalar Docker (una sola vez)

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
exit
```

Vuelva a conectarse por SSH para que el permiso del grupo `docker` quede activo, y verifique:

```bash
docker --version
docker compose version
```

Solo si la instancia tiene 1 GB de RAM (`t2.micro`), agregue 2 GB de swap:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2.4 Descargar el código

```bash
cd ~
git clone https://github.com/felipedbthecreator/Proyecto-despliegue-soluciones-analytics.git
cd Proyecto-despliegue-soluciones-analytics
```

Si el repositorio ya estaba clonado:

```bash
cd ~/Proyecto-despliegue-soluciones-analytics
git pull origin main
```

### 2.5 Construir y levantar los contenedores

```bash
docker compose up -d --build
```

La primera vez tarda entre 3 y 6 minutos, porque descarga las imágenes base e instala las dependencias. Compose:

1. Construye `api-rendimiento` con `api/Dockerfile`: Python 3.13, scikit-learn 1.9.1, los tres modelos de `models/` y los datos de referencia.
2. Construye `tablero-rendimiento` con `tablero/Dockerfile` (Dash servido con Gunicorn).
3. Arranca la API, espera a que `/health` responda y luego arranca el tablero.

Ambos servicios quedan con `restart: unless-stopped`, así que se reinician solos si la instancia se reinicia.

### 2.6 Verificar el despliegue

En la instancia:

```bash
docker compose ps
curl -s localhost:8001/health
```

`api` debe aparecer como `running (healthy)` y `tablero` como `running`. La respuesta de `/health` debe ser:

```json
{"status":"ok","modelo":"rendimiento-v1","modelos":{"arroz":"rendimiento-arroz-hgb-v1","papa":"rendimiento-papa-hgb-v1","cana":"rendimiento-cana-hgb-v1"}}
```

Desde el navegador de su computador:

| Dirección | Qué debe verse |
|---|---|
| `http://<IP-PUBLICA>:8001/docs` | Documentación interactiva de la API. En `POST /predict` → *Try it out* se puede enviar una petición de prueba. |
| `http://<IP-PUBLICA>:8050` | El tablero, con la **franja verde** *Predicciones servidas por la API del modelo*. |

Petición de prueba a la API:

```bash
curl -s -X POST http://<IP-PUBLICA>:8001/predict \
  -H "Content-Type: application/json" \
  -d '{"municipio":"Pueblo Nuevo","cod_mpio":23570,"cultivo":"arroz","variante":"secano_man","periodo":"2026B","escenario":"nino"}'
```

Respuesta esperada: `{"rendimiento_t_ha":1.51,"intervalo_80":[1.179,1.931],"modelo":"rendimiento-arroz-hgb-v1",...}`.

## 3. Instalación local (sin EC2)

### 3.1 Con Docker

Con Docker Desktop abierto, desde la raíz del repositorio:

```bash
docker compose up -d --build
```

- API: `http://localhost:8001/docs`
- Tablero: `http://localhost:8050`

### 3.2 Sin Docker

Necesita Python 3.13 (la misma versión con que se serializaron los modelos). Use dos terminales desde la raíz del repositorio.

Terminal 1, la API:

```bash
python3.13 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt
uvicorn api.main:app --port 8001
```

Terminal 2, el tablero:

```bash
source .venv/bin/activate
pip install -r tablero/requirements.txt
cd tablero
API_URL=http://localhost:8001 python app.py              # Windows PowerShell: $env:API_URL="http://localhost:8001"; python app.py
```

## 4. Variables de configuración

| Variable | Servicio | Valor por defecto | Uso |
|---|---|---|---|
| `API_URL` | Tablero | `http://api:8001` en Compose | Dirección de la API. También se puede cambiar desde el panel del tablero. |
| `RUTA_MODELOS` | API | `models/` | Carpeta con `rendimiento_<cultivo>.pkl/.json`. |
| `RUTA_DATASET` | API | `tablero/datos/dataset_modelo.csv` | Municipios y departamentos válidos. |
| `RUTA_RONI` | API | `tablero/datos/roni.txt` | RONI de NOAA/CPC para el periodo anterior. |

## 5. Operación

| Tarea | Comando (en la raíz del repositorio) |
|---|---|
| Ver el estado | `docker compose ps` |
| Ver los registros | `docker compose logs -f api` o `docker compose logs -f tablero` |
| Actualizar a la última versión | `git pull origin main && docker compose up -d --build` |
| Reiniciar | `docker compose restart` |
| Apagar | `docker compose down` |

**Actualizar los modelos.** Corra `src/tuning.py` (ver `docs/hiperparametros.md`), suba los nuevos `models/*.pkl` y `.json` al repositorio y ejecute en la instancia `git pull origin main && docker compose up -d --build`. La versión de scikit-learn de `api/requirements.txt` debe ser la misma de `requirements-modelo.txt`.

**Apagar la instancia.** Ejecute `docker compose down` y luego, en la consola de AWS, *Instance state* → **Stop**. No use *Terminate*: borra la máquina.

## 6. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| El navegador no carga `:8001` ni `:8050` | Puerto cerrado o IP cambiada | Revise las reglas de entrada (2.1) y la IP pública actual. |
| `permission denied ... docker.sock` | El usuario no está en el grupo `docker` | Salga y vuelva a entrar por SSH, o use `sudo docker compose ...`. |
| La construcción se detiene o la instancia deja de responder | Falta de memoria | Agregue la swap de la sección 2.3 o use una instancia más grande. |
| `api` queda en `unhealthy` o se reinicia | Error al cargar los modelos | `docker compose logs api`. Revise que `models/` tenga los seis archivos y que las versiones coincidan con `requirements-modelo.txt`. |
| El tablero muestra la **franja amarilla** | El tablero no llega a la API | Haga clic en **Probar** en el panel de conexión. Si sigue, revise `docker compose ps` y `docker compose logs api`. |
| La API responde 404 *Municipio no está en la base EVA* | Código DANE sin registros | Use un municipio que aparezca en el tablero. |
| La API responde 422 | Combinación inválida (por ejemplo, variante de papa con cultivo arroz, o caña con un periodo semestral) | Revise los códigos en `/docs`. |
