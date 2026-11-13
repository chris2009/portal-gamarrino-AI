# -*- coding: utf-8 -*-
"""
Descarga los modelos locales de los guardrails (DetectJailbreak y
GuardrailsPII) durante la construccion de la imagen Docker, para que el
primer usuario no espere esa descarga. No necesita OPENAI_API_KEY: solo crea
los validadores y los corre una vez con un texto de prueba.
"""
from guardrails import Guard
from guardrails_ai.detect_jailbreak import DetectJailbreak
from guardrails_ai.guardrails_pii import GuardrailsPII

Guard().use(DetectJailbreak(use_local=True, on_fail="noop")).validate("busco polos basicos")
Guard().use(GuardrailsPII(entities=["EMAIL_ADDRESS", "CREDIT_CARD", "ES_NIF"], on_fail="fix")).validate(
    "escribe a ventas@tienda.com"
)
print("Modelos de los guardrails descargados.")
