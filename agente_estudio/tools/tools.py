import json
from datetime import date, datetime
from pathlib import Path

from ddgs import DDGS
from ddgs.exceptions import DDGSException

# Las tareas se guardan en un archivo JSON dentro de la carpeta del agente
ARCHIVO_TAREAS = Path(__file__).parent.parent / "tareas.json"


def leer_tareas() -> list:
    if not ARCHIVO_TAREAS.exists():
        return []
    try:
        return json.loads(ARCHIVO_TAREAS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def guardar_tareas(tareas: list) -> None:
    ARCHIVO_TAREAS.write_text(json.dumps(tareas, ensure_ascii=False, indent=2), encoding="utf-8")


def agregar_tarea(materia: str, descripcion: str, fecha_entrega: str) -> dict:
    """
    Herramienta para registrar una tarea, entrega o examen.
    Args:
        materia: str -> nombre de la materia, por ejemplo "Matemática".
        descripcion: str -> qué hay que hacer o estudiar.
        fecha_entrega: str -> fecha límite en formato AAAA-MM-DD, por ejemplo "2026-12-05".
    """
    try:
        if not materia.strip() or not descripcion.strip():
            return {"estado": "error", "mensaje": "La materia y la descripción no pueden estar vacías."}

        try:
            fecha = datetime.strptime(fecha_entrega.strip(), "%Y-%m-%d").date()
        except ValueError:
            return {"estado": "error", "mensaje": f"La fecha '{fecha_entrega}' no es válida. Tiene que tener el formato AAAA-MM-DD."}

        if fecha < date.today():
            return {"estado": "error", "mensaje": f"La fecha {fecha} ya pasó. Indicá una fecha de hoy en adelante."}

        tareas = leer_tareas()
        for t in tareas:
            mismo = t["materia"].lower() == materia.strip().lower() and t["descripcion"].lower() == descripcion.strip().lower()
            if mismo and not t["completada"]:
                return {"estado": "error", "mensaje": f"Esa tarea ya está registrada con el id {t['id']}."}

        nuevo_id = max([t["id"] for t in tareas], default=0) + 1
        tarea = {
            "id": nuevo_id,
            "materia": materia.strip(),
            "descripcion": descripcion.strip(),
            "fecha_entrega": str(fecha),
            "completada": False,
        }
        tareas.append(tarea)
        guardar_tareas(tareas)
        return {"estado": "ok", "mensaje": "Tarea registrada.", "tarea": tarea}
    except Exception as e:
        print("Error interno en agregar_tarea:", e)
        return {"estado": "error", "mensaje": f"Error interno al guardar la tarea: {e}"}


def listar_tareas(materia: str = "", solo_pendientes: bool = True) -> dict:
    """
    Herramienta para consultar las tareas registradas, ordenadas por fecha de entrega.
    Indica cuántos días faltan para cada una.
    Args:
        materia: str -> filtra por materia. Vacío para ver todas.
        solo_pendientes: bool -> True para ver solo las que no están completadas.
    """
    try:
        tareas = leer_tareas()

        if materia.strip():
            tareas = [t for t in tareas if materia.strip().lower() in t["materia"].lower()]
        if solo_pendientes:
            tareas = [t for t in tareas if not t["completada"]]

        if not tareas:
            texto = f" de {materia}" if materia.strip() else ""
            return {"estado": "vacio", "mensaje": f"No hay tareas{texto} para mostrar."}

        tareas = sorted(tareas, key=lambda t: t["fecha_entrega"])
        for t in tareas:
            dias = (date.fromisoformat(t["fecha_entrega"]) - date.today()).days
            t["dias_restantes"] = dias
        return {"estado": "ok", "cantidad": len(tareas), "tareas": tareas}
    except Exception as e:
        print("Error interno en listar_tareas:", e)
        return {"estado": "error", "mensaje": f"Error interno al leer las tareas: {e}"}


def completar_tarea(busqueda: str) -> dict:
    """
    Herramienta para marcar como completada una tarea pendiente.
    Busca la tarea por la materia o por palabras de su descripción.
    Args:
        busqueda: str -> materia o palabras de la tarea, por ejemplo "cinemática" o "Física".
    """
    try:
        if not busqueda.strip():
            return {"estado": "error", "mensaje": "Indicá la materia o alguna palabra de la tarea que querés completar."}

        # Se buscan las palabras de 4 letras o más, para ignorar "de", "la", "el", etc.
        palabras = [p for p in busqueda.lower().split() if len(p) >= 4]
        if not palabras:
            palabras = [busqueda.strip().lower()]

        # Cada tarea pendiente suma un punto por cada palabra que coincide
        tareas = leer_tareas()
        puntajes = []
        for t in tareas:
            texto_tarea = (t["materia"] + " " + t["descripcion"]).lower()
            puntos = sum(1 for p in palabras if p in texto_tarea)
            if not t["completada"] and puntos > 0:
                puntajes.append((puntos, t))

        # Se quedan las que tienen más coincidencias
        mejor = max([puntos for puntos, t in puntajes], default=0)
        coincidencias = [t for puntos, t in puntajes if puntos == mejor]

        if not coincidencias:
            return {"estado": "vacio", "mensaje": f"No hay ninguna tarea pendiente que coincida con '{busqueda}'."}

        if len(coincidencias) > 1:
            opciones = [f"{t['materia']}: {t['descripcion']}" for t in coincidencias]
            return {"estado": "error", "mensaje": "Hay varias tareas que coinciden. Preguntale al usuario cuál es.", "opciones": opciones}

        tarea = coincidencias[0]
        tarea["completada"] = True
        guardar_tareas(tareas)
        return {"estado": "ok", "mensaje": "Tarea marcada como completada.", "tarea": tarea}
    except Exception as e:
        print("Error interno en completar_tarea:", e)
        return {"estado": "error", "mensaje": f"Error interno al actualizar la tarea: {e}"}


def buscar_en_internet(consulta: str, max_resultados: int = 5) -> dict:
    """
    Herramienta para buscar en internet material de estudio usando DuckDuckGo.
    Args:
        consulta: str -> lo que hay que buscar.
        max_resultados: int -> cantidad de resultados, entre 1 y 10.
    """
    try:
        if not consulta.strip():
            return {"estado": "error", "mensaje": "La consulta no puede estar vacía."}
        if max_resultados < 1 or max_resultados > 10:
            return {"estado": "error", "mensaje": "max_resultados tiene que estar entre 1 y 10."}

        # El buscador a veces falla o tarda, por eso se prueba dos veces
        resultados = []
        for intento in range(2):
            try:
                resultados = DDGS().text(query=consulta, max_results=max_resultados)
                break
            except DDGSException:
                resultados = []

        if not resultados:
            return {"estado": "vacio", "mensaje": f"No se encontraron resultados para '{consulta}'. Probá con otras palabras."}

        return {
            "estado": "ok",
            "resultados": [
                {"titulo": r.get("title"), "enlace": r.get("href"), "resumen": (r.get("body") or "")[:300]}
                for r in resultados
            ],
        }
    except Exception as e:
        print("Error interno en buscar_en_internet:", e)
        return {"estado": "error", "mensaje": f"No se pudo buscar en internet: {e}"}
