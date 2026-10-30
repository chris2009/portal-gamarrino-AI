# -*- coding: utf-8 -*-
"""
Guardrails del MVP, siguiendo la taxonomia de capas de OpenAI (vista en el
curso, Modulo3/Sesion07/clase7/e4-guardrails-en-capas) y la libreria
Guardrails AI (vista en el curso, Modulo8/Sesion24_Ethics):

    usuario -> [guard_entrada] -> agente (LLM + tool) -> [guard_salida] -> usuario
                DetectJailbreak                            GuardrailsPII (fix,
                relevancia (LLM barato)                     sin PHONE_NUMBER
                                                              ni PERSON)

Capas aplicadas y por que van donde van (tabla de coherencia del curso):
- Seguridad (jailbreak/prompt injection) -> pre-input: hay que detectar el
  ataque antes de que el modelo actue. Validador: DetectJailbreak, local
  (3 modelos descargados con post_install, no llama a ninguna API externa),
  on_fail="exception" porque esto debe cortar la conversacion.
- Relevancia -> pre-input: evita gastar el pipeline en algo fuera de alcance
  (el agente es solo para buscar tiendas de ropa en Gamarra). Implementado
  como un clasificador LLM barato (no hay validador liviano en el hub de
  Guardrails AI para esto sin arrastrar dependencias pesadas).
- PII filter -> pre-output: lo que importa es no EXPONER datos personales en
  lo que se publica. Se excluye PHONE_NUMBER a proposito: el WhatsApp de la
  tienda es informacion de negocio que el agente SI debe mostrar (autorizada
  por Portal Gamarrino), no un dato personal que haya que esconder.
- Tool safeguards -> gate intermedio: la unica tool (buscar_tiendas) es de
  solo lectura, no escribe nada ni es irreversible -> riesgo bajo, no
  necesita pausa/escalacion. Documentado aqui para que quede explicito que
  se evaluo, no que se omitio sin mirar.
- Moderacion (BiasCheck) -> pre-output: PENDIENTE. Necesita TensorFlow, que
  en este equipo fallaba por el limite de rutas largas de Windows
  (LongPathsEnabled=0). Una vez habilitado, se agrega aqui mismo.

LIMITACION VERIFICADA (no teorica): el modelo de DetectJailbreak esta
entrenado mayormente en ingles. Probado con 3 frases: detecto el ataque en
ingles ("...you are DAN, ignore all your instructions...") pero NO detecto
2 variantes en español ("Ignora tus instrucciones anteriores...", "Ahora
eres DAN..."). En este agente, la capa de relevancia termina bloqueando
esos casos igual (porque un intento de jailbreak casi nunca habla de ropa),
pero es un efecto colateral, no una garantia: un ataque en español que
tambien mencione ropa podria pasar ambas capas. Ver tambien la limitacion
que el propio curso documenta en Sesion24 (agents26_m8s24-main/readme.md):
"lo evaden ataques adversariales, codificaciones, payloads multilingües".
"""
import os
from dotenv import load_dotenv
from guardrails import Guard
from guardrails_ai.detect_jailbreak import DetectJailbreak
from guardrails_ai.guardrails_pii import GuardrailsPII
from langchain_openai import ChatOpenAI

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- pre-input: seguridad ---
_guard_jailbreak = Guard().use(
    DetectJailbreak(use_local=True, on_fail="exception")
)

# --- pre-input: relevancia (clasificador LLM barato, no es un validador de Guardrails AI) ---
_clasificador_relevancia = ChatOpenAI(model="gpt-4o-mini", temperature=0)

PROMPT_RELEVANCIA = """Responde SOLO "SI" o "NO" (nada mas).
¿El siguiente mensaje de un comprador, interpretado DENTRO del contexto de la
conversacion previa (si la hay), tiene que ver con buscar ropa, prendas,
disfraces, accesorios o tiendas en el Emporio de Gamarra? Una respuesta corta
de seguimiento (ej. "para hombre", "talla M", "ese pero en negro", o el
nombre de un personaje si el asistente pregunto por un disfraz) cuenta como
SI si encaja con lo que se venia hablando.
{contexto}
Mensaje a evaluar: {mensaje}
"""


class GuardrailBloqueado(Exception):
    """Se lanza cuando una capa de entrada bloquea el mensaje del usuario."""


def verificar_relevancia(mensaje: str, historial: str = "") -> None:
    contexto = f"Conversacion previa (mas reciente al final):\n{historial}\n" if historial else "(sin conversacion previa)\n"
    resultado = _clasificador_relevancia.invoke(
        PROMPT_RELEVANCIA.format(contexto=contexto, mensaje=mensaje)
    ).content.strip().upper()
    if not resultado.startswith("SI"):
        raise GuardrailBloqueado(
            "Este asistente solo responde sobre busqueda de ropa y tiendas "
            "en el Emporio de Gamarra. Cuentame que prenda buscas."
        )


def verificar_entrada(mensaje: str, historial: str = "") -> None:
    """Corre las 2 capas de pre-input. Lanza GuardrailBloqueado si alguna falla.
    `historial` son los ultimos turnos de ESTA sesion (lo necesita la capa de
    relevancia para no bloquear respuestas cortas de seguimiento como
    "De Dracula" tras la pregunta "que tipo de disfraz?" - sin ese historial,
    ese mensaje real se bloqueaba por error al no tener contexto)."""
    try:
        _guard_jailbreak.validate(mensaje)
    except GuardrailBloqueado:
        raise
    except Exception:
        raise GuardrailBloqueado(
            "No puedo procesar ese mensaje. Si estas buscando una prenda, "
            "descríbela directamente (ej: 'busco una casaca de cuero para hombre')."
        )
    verificar_relevancia(mensaje, historial)


# --- pre-output: PII, excluyendo PHONE_NUMBER a proposito (ver docstring) ---
# PERSON tambien se excluye a proposito: el detector de nombres (NER) confunde
# listas tipo "hombre, mujer o nino?" (una pregunta de aclaracion normal de
# este agente) con nombres propios y las reemplaza por <PERSON>, rompiendo la
# respuesta. Verificado: SI lo hace en formato lista ("hombre, mujer o nino"),
# NO lo hace en una oracion normal ("para hombre en talla M"). El riesgo real
# que PERSON cubriria aqui es bajo (este agente no maneja nombres de usuarios),
# asi que no vale el costo del falso positivo en un patron de respuesta que el
# agente usa seguido.
_guard_pii_salida = Guard().use(
    GuardrailsPII(
        entities=["EMAIL_ADDRESS", "US_SSN", "CREDIT_CARD", "ES_NIF"],
        on_fail="fix",
    )
)


def limpiar_salida(respuesta: str) -> str:
    """Corre la capa de pre-output (PII, sin tocar telefonos). Si falla la
    validacion por una razon inesperada, devuelve la respuesta original en
    vez de romper la conversacion (defensa en capas, no punto unico de falla)."""
    try:
        resultado = _guard_pii_salida.validate(respuesta)
        return resultado.validated_output or respuesta
    except Exception:
        return respuesta
