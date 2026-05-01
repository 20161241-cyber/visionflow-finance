import os
import resend
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def enviar_bienvenida_premium(email_destino: str, nombre_usuario: str, tipo_licencia: str = "Premium") -> bool:
    """
    Envía un correo de Bienvenida Transaccional usando la API de Resend.
    """
    # 1. Cargar API Key
    try:
        current_dir = Path(__file__).parent.parent
        key_file = current_dir / "resend_api_key.txt"
        
        if key_file.exists():
            resend.api_key = key_file.read_text().strip()
        else:
            resend.api_key = os.getenv("RESEND_API_KEY", "")
    except Exception:
        logger.error("Error al intentar leer la API Key de Resend.")
        return False
        
    if not resend.api_key:
        logger.warning("No se encontró la API Key de Resend (resend_api_key.txt). Omitiendo envío de correo.")
        return False

    # 2. Diseñar el cuerpo HTML del correo
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; background-color: #0A0F1E; color: white; border-radius: 12px;">
        <h1 style="color: #00F5C4; text-align: center;">¡Bienvenido a VisionFlow Finance!</h1>
        <p style="font-size: 16px;">Hola <strong>{nombre_usuario}</strong>,</p>
        <p style="font-size: 16px; color: #E2E8F0;">
            Tu registro ha sido exitoso. Has sido dado de alta en nuestro sistema con la licencia 
            <span style="background-color: #7B61FF; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{tipo_licencia}</span>.
        </p>
        <br/>
        <div style="background-color: #111827; padding: 15px; border-radius: 8px;">
            <h3 style="color: #FFD166; margin-top: 0;">Lo que incluye tu licencia:</h3>
            <ul style="color: #A0AEC0;">
                <li>Predicción de Quiebra Financiera</li>
                <li>Detección de Gasto Hormiga con Llama 3.2 Vision</li>
                <li>Almacenamiento Ilimitado de Recibos en la Nube</li>
            </ul>
        </div>
        <p style="font-size: 14px; text-align: center; color: #718096; margin-top: 30px;">
            Con cariño,<br/>El equipo de Inteligencia Financiera
        </p>
    </div>
    """

    # 3. Enviar el correo
    try:
        params: resend.Emails.SendParams = {
            "from": "VisionFlow Finance <onboarding@visionflow.finance>",
            "to": [email_destino],
            "subject": f"¡Tu licencia {tipo_licencia} está activa, {nombre_usuario}!",
            "html": html_content,
        }
        email_response = resend.Emails.send(params)
        logger.info(f"Correo enviado exitosamente a {email_destino}: {email_response}")
        return True
    except Exception as e:
        logger.error(f"Fallo al enviar correo de bienvenida: {e}")
        return False
