import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask, request, jsonify
import logging

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración
TOKEN = os.environ.get('BOT_TOKEN')
WEBAPP_URL = "https://cbot-upslp.onrender.com"

# NO configurar el webhook aquí, solo verificar el token
if not TOKEN:
    logger.error("❌ ERROR: BOT_TOKEN no encontrado")
    # Para desarrollo local puedes usar un token temporal
    TOKEN = "8437171681:AAH3K_6vtwrF2E4w6Fcek1iwPJwPp-ubi94"

# Estados de conversación
(
    MENU, SELECCION_SEMESTRE, SELECCION_MATERIAS, 
    AGREGAR_CALIFICACION, CONFIRMAR_ELIMINAR, ESTADISTICAS
) = range(6)

# Plan de estudios UPSLP (sin créditos visibles)
PLAN_ESTUDIOS = {
    1: [
        {"nombre": "Matemáticas I", "creditos": 4, "tipo": "Básica"},
        {"nombre": "Física I", "creditos": 4, "tipo": "Básica"},
        {"nombre": "Inglés I", "creditos": 4, "tipo": "Inglés"},
        {"nombre": "Desarrollo del Pensamiento Crítico", "creditos": 7, "tipo": "Núcleo General"},
        {"nombre": "Introducción a la Computación", "creditos": 4, "tipo": "Básica"},
        {"nombre": "Proyecto Integrador de Ingeniería I", "creditos": 7, "tipo": "Proyecto"}
    ],
    2: [
        {"nombre": "Matemáticas II", "creditos": 8, "tipo": "Básica"},
        {"nombre": "Física II", "creditos": 8, "tipo": "Básica"},
        {"nombre": "Inglés II", "creditos": 7, "tipo": "Inglés"},
        {"nombre": "Comunicación e Investigación", "creditos": 7, "tipo": "Núcleo General"},
        {"nombre": "Programación I", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Programación Web I", "creditos": 7, "tipo": "Núcleo Optativo"}
    ],
    3: [
        {"nombre": "Matemáticas III", "creditos": 9, "tipo": "Básica"},
        {"nombre": "Matemáticas Discretas", "creditos": 9, "tipo": "Básica"},
        {"nombre": "Inglés III", "creditos": 7, "tipo": "Inglés"},
        {"nombre": "Química", "creditos": 7, "tipo": "Básica"},
        {"nombre": "Programación II", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Programación Web II", "creditos": 7, "tipo": "Núcleo Optativo"}
    ],
    4: [
        {"nombre": "Probabilidad y Estadística", "creditos": 7, "tipo": "Básica"},
        {"nombre": "Circuitos Básicos", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Inglés IV", "creditos": 5, "tipo": "Inglés"},
        {"nombre": "Historia-Valores", "creditos": 6, "tipo": "Núcleo General"},
        {"nombre": "Programación III", "creditos": 9, "tipo": "Ingeniería"},
        {"nombre": "Proyecto Integrador de Ingeniería II", "creditos": 7, "tipo": "Proyecto"}
    ],
    5: [
        {"nombre": "Matemáticas IV", "creditos": 8, "tipo": "Básica"},
        {"nombre": "Sistemas Digitales", "creditos": 8, "tipo": "Ingeniería"},
        {"nombre": "Inglés V", "creditos": 7, "tipo": "Inglés"},
        {"nombre": "Análisis y Diseño de Algoritmos", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Modelado", "creditos": 7, "tipo": "Núcleo Optativo"}
    ],
    6: [
        {"nombre": "Taller de Desarrollo Empresarial", "creditos": 7, "tipo": "Sociales"},
        {"nombre": "Aplicaciones de Computación", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Organización y Compensación", "creditos": 7, "tipo": "Núcleo General"},
        {"nombre": "Laboratorio de Programación", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Ingeniería de Software I", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Proyecto Integrador de Ingeniería III", "creditos": 7, "tipo": "Proyecto"}
    ],
    7: [
        {"nombre": "Taller de Comunicación", "creditos": 7, "tipo": "Sociales"},
        {"nombre": "Organización Computacional", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Programación Web III", "creditos": 7, "tipo": "Núcleo Optativo"},
        {"nombre": "Base de Datos I", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Ingeniería de Software II", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Taller de Creatividad y Emprendedurismo", "creditos": 7, "tipo": "Sociales"}
    ],
    8: [
        {"nombre": "Desarrollo de Competitividad", "creditos": 7, "tipo": "Núcleo General"},
        {"nombre": "Redes de Computadoras", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Minería de Datos", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Inteligencia Artificial I", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Seguridad Informática", "creditos": 7, "tipo": "Núcleo Optativo"},
        {"nombre": "Proyecto Integrador de Ingeniería IV", "creditos": 7, "tipo": "Proyecto"}
    ],
    9: [
        {"nombre": "Computación Gráfica", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Sistemas Virtuales", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Computación Emergente", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Inteligencia Artificial II", "creditos": 7, "tipo": "Ingeniería"},
        {"nombre": "Base de Datos Distribuidas", "creditos": 8, "tipo": "Núcleo Optativo"},
        {"nombre": "Proyecto Profesional", "creditos": 8, "tipo": "Proyecto"},
        {"nombre": "Residencia Profesional", "creditos": 10, "tipo": "Residencia"}
    ]
}

# Inicializar base de datos
def init_db():
    conn = sqlite3.connect('materias_upslp.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            semestre INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            creditos INTEGER,
            tipo TEXT,
            estado TEXT DEFAULT 'cursando',
            calificacion REAL,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Teclados
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["📚 Agregar Materias", "📖 Ver Mis Materias"],
        ["📊 Avance Académico", "⭐ Agregar Calificación"],
        ["🗑️ Eliminar Materia", "📈 Estadísticas"],
        ["ℹ️ Plan de Estudios"]
    ], resize_keyboard=True)

def back_keyboard():
    return ReplyKeyboardMarkup([["🔙 Menú Principal"]], resize_keyboard=True)

def semestres_keyboard():
    keyboard = [[f"Semestre {i}"] for i in range(1, 10)]
    keyboard.append(["🔙 Menú Principal"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def materias_keyboard(semestre):
    materias_semestre = PLAN_ESTUDIOS.get(semestre, [])
    keyboard = []
    
    # Dividir en filas de 2 materias
    for i in range(0, len(materias_semestre), 2):
        row = []
        if i < len(materias_semestre):
            row.append(materias_semestre[i]['nombre'])
        if i + 1 < len(materias_semestre):
            row.append(materias_semestre[i + 1]['nombre'])
        if row:
            keyboard.append(row)
    
    # Botones de control
    keyboard.append(["✅ Terminar selección"])
    keyboard.append(["🔙 Menú Principal"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def confirmacion_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Sí, eliminar"],
        ["❌ No, cancelar"],
        ["🔙 Menú Principal"]
    ], resize_keyboard=True)

# --- FUNCIONES DE BASE DE DATOS ---
def agregar_materia_db(user_id, semestre, nombre, creditos, tipo):
    conn = sqlite3.connect('materias_upslp.db')
    cursor = conn.cursor()
    
    # Verificar si ya existe
    cursor.execute('''
        SELECT id FROM materias 
        WHERE user_id = ? AND nombre = ? AND semestre = ?
    ''', (user_id, nombre, semestre))
    
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO materias (user_id, semestre, nombre, creditos, tipo)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, semestre, nombre, creditos, tipo))
    
    conn.commit()
    conn.close()

def obtener_materias_usuario(user_id):
    conn = sqlite3.connect('materias_upslp.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, semestre, nombre, creditos, tipo, estado, calificacion 
        FROM materias 
        WHERE user_id = ? 
        ORDER BY semestre, nombre
    ''', (user_id,))
    
    materias = cursor.fetchall()
    conn.close()
    return materias

def eliminar_materia_db(materia_id, user_id):
    conn = sqlite3.connect('materias_upslp.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM materias WHERE id = ? AND user_id = ?', (materia_id, user_id))
    affected = cursor.rowcount
    
    conn.commit()
    conn.close()
    return affected > 0

def actualizar_calificacion_db(materia_id, user_id, calificacion):
    conn = sqlite3.connect('materias_upslp.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE materias 
        SET calificacion = ?, estado = ? 
        WHERE id = ? AND user_id = ?
    ''', (calificacion, "aprobada" if calificacion >= 60 else "reprobada", materia_id, user_id))
    
    conn.commit()
    conn.close()

# --- PALABRAS CLAVE UNIVERSALES ---
async def check_volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verificar si el usuario quiere volver al menú"""
    text = update.message.text.lower()
    
    palabras_volver = [
        "menu", "menú", "principal", "volver", "atrás", "atras", 
        "inicio", "home", "regresar", "back", "cancelar"
    ]
    
    if any(palabra in text for palabra in palabras_volver):
        await update.message.reply_text(
            "🏠 Volviendo al menú principal...",
            reply_markup=main_keyboard()
        )
        return MENU
    
    return None

# --- FLUJOS PRINCIPALES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensaje de bienvenida y menú principal"""
    welcome_text = """
    🎓 **¡Bienvenido al Sistema de Gestión Académica UPSLP!** 🎓

    **Comandos disponibles:**

    📚 **Agregar Materias** - Registrar materias cursadas (varias a la vez)
    📖 **Ver Mis Materias** - Tu historial académico  
    📊 **Avance Académico** - Progreso de tu carrera
    ⭐ **Agregar Calificación** - Registrar calificaciones
    🗑️ **Eliminar Materia** - Remover materias
    📈 **Estadísticas** - Estadísticas académicas
    ℹ️ **Plan de Estudios** - Ver plan completo

    💡 **Tips:**
    - Usa el teclado para navegar
    - Escribe "menu" en cualquier momento para volver
    - Puedes agregar varias materias a la vez
    """
    await update.message.reply_text(welcome_text, reply_markup=main_keyboard())
    return MENU

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección del menú"""
    # Primero verificar si quiere volver al menú
    volver = await check_volver_menu(update, context)
    if volver is not None:
        return volver
        
    text = update.message.text
    
    if "agregar materias" in text.lower():
        await update.message.reply_text(
            "📅 **Selecciona el semestre:**",
            reply_markup=semestres_keyboard()
        )
        return SELECCION_SEMESTRE
        
    elif "ver mis materias" in text.lower():
        await mostrar_mis_materias(update, context)
        return MENU
        
    elif "avance académico" in text.lower() or "avance" in text.lower():
        await mostrar_avance(update, context)
        return MENU
        
    elif "agregar calificación" in text.lower() or "agregar calificacion" in text.lower():
        await iniciar_calificacion(update, context)
        return AGREGAR_CALIFICACION
        
    elif "eliminar" in text.lower():
        await iniciar_eliminacion(update, context)
        return CONFIRMAR_ELIMINAR
        
    elif "estadísticas" in text.lower() or "estadisticas" in text.lower():
        await mostrar_estadisticas(update, context)
        return MENU
        
    elif "plan de estudios" in text.lower():
        await mostrar_plan_estudios(update, context)
        return MENU
    
    return MENU

# --- FLUJO AGREGAR VARIAS MATERIAS ---
async def handle_seleccion_semestre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de semestre"""
    volver = await check_volver_menu(update, context)
    if volver is not None:
        return volver
    
    text = update.message.text
    
    try:
        semestre = int(text.split(" ")[1])
        context.user_data['semestre'] = semestre
        context.user_data['materias_seleccionadas'] = []  # Lista para materias seleccionadas
        
        await update.message.reply_text(
            f"📚 **Selecciona las materias del {semestre}° Semestre:**\n\n"
            f"💡 **Puedes seleccionar varias materias**\n"
            f"✅ **Terminar selección** cuando hayas terminado",
            reply_markup=materias_keyboard(semestre)
        )
        return SELECCION_MATERIAS
        
    except Exception as e:
        await update.message.reply_text("❌ Error al seleccionar semestre.", reply_markup=main_keyboard())
        return MENU

async def handle_seleccion_materias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar selección de múltiples materias"""
    volver = await check_volver_menu(update, context)
    if volver is not None:
        return volver
    
    text = update.message.text
    user_id = update.message.from_user.id
    semestre = context.user_data['semestre']
    materias_seleccionadas = context.user_data.get('materias_seleccionadas', [])
    
    if text == "✅ Terminar selección":
        if not materias_seleccionadas:
            await update.message.reply_text(
                "❌ No seleccionaste ninguna materia.",
                reply_markup=main_keyboard()
            )
            return MENU
        
        # Agregar todas las materias seleccionadas a la base de datos
        materias_agregadas = []
        for materia_nombre in materias_seleccionadas:
            # Buscar la materia en el plan
            materia_info = None
            for materia in PLAN_ESTUDIOS[semestre]:
                if materia['nombre'] == materia_nombre:
                    materia_info = materia
                    break
            
            if materia_info:
                # Verificar si ya existe
                materias_existentes = obtener_materias_usuario(user_id)
                existe = any(mat[2] == materia_nombre and mat[1] == semestre for mat in materias_existentes)
                
                if not existe:
                    agregar_materia_db(user_id, semestre, materia_nombre, materia_info['creditos'], materia_info['tipo'])
                    materias_agregadas.append(materia_nombre)
        
        # Mostrar resumen
        if materias_agregadas:
            response = "✅ **Materias agregadas exitosamente!**\n\n"
            for materia in materias_agregadas:
                response += f"📚 {materia}\n"
            response += f"\n🎯 Semestre: {semestre}°\n"
            response += f"📈 Estado: Cursando"
        else:
            response = "ℹ️ **Todas las materias seleccionadas ya estaban registradas.**"
        
        await update.message.reply_text(response, reply_markup=main_keyboard())
        return MENU
    
    else:
        # Agregar materia a la lista de seleccionadas
        if text not in materias_seleccionadas:
            materias_seleccionadas.append(text)
            context.user_data['materias_seleccionadas'] = materias_seleccionadas
            
            await update.message.reply_text(
                f"✅ **{text}** agregada a la selección.\n\n"
                f"📋 **Materias seleccionadas ({len(materias_seleccionadas)}):**\n" +
                "\n".join([f"• {m}" for m in materias_seleccionadas]) +
                f"\n\n💡 Continúa seleccionando o presiona **'Terminar selección'**",
                reply_markup=materias_keyboard(semestre)
            )
        else:
            await update.message.reply_text(
                f"ℹ️ **{text}** ya está en tu selección.\n\n"
                f"💡 Selecciona otra materia o presiona **'Terminar selección'**",
                reply_markup=materias_keyboard(semestre)
            )
        
        return SELECCION_MATERIAS

# --- FLUJO VER MATERIAS ---
async def mostrar_mis_materias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar materias del usuario"""
    user_id = update.message.from_user.id
    materias = obtener_materias_usuario(user_id)
    
    if not materias:
        await update.message.reply_text(
            "📭 No tienes materias registradas.\n💡 Usa 'Agregar Materias' para comenzar!",
            reply_markup=main_keyboard()
        )
        return
    
    response = "📖 **Tus Materias Registradas:**\n\n"
    for id, semestre, nombre, creditos, tipo, estado, calificacion in materias:
        response += f"🎯 **{nombre}**\n"
        response += f"   📅 Semestre: {semestre}°\n"
        response += f"   🏷️ Tipo: {tipo}\n"
        response += f"   📈 Estado: {estado}\n"
        if calificacion:
            status = "✅ Aprobada" if calificacion >= 60 else "❌ Reprobada"
            response += f"   ⭐ Calificación: {calificacion}/100 ({status})\n"
        response += "\n"
    
    await update.message.reply_text(response, reply_markup=main_keyboard())

# --- FLUJO AGREGAR CALIFICACIÓN (CORREGIDO) ---
async def iniciar_calificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar proceso de calificación"""
    user_id = update.message.from_user.id
    materias = obtener_materias_usuario(user_id)
    
    # Filtrar materias sin calificación
    materias_sin_calificar = [m for m in materias if m[6] is None]
    
    if not materias_sin_calificar:
        await update.message.reply_text(
            "✅ ¡Todas tus materias ya tienen calificación!",
            reply_markup=main_keyboard()
        )
        return MENU
    
    # Crear teclado con materias sin calificar
    keyboard = []
    materias_dict = {}
    
    for id, semestre, nombre, _, _, _, _ in materias_sin_calificar:
        keyboard.append([f"Calificar: {nombre} (S{semestre})"])
        materias_dict[f"Calificar: {nombre} (S{semestre})"] = {
            'id': id,
            'nombre': nombre,
            'semestre': semestre
        }
    
    keyboard.append(["🔙 Menú Principal"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data['materias_calificar'] = materias_dict
    context.user_data['esperando_calificacion'] = False
    
    await update.message.reply_text(
        "📝 **Selecciona una materia para calificar:**",
        reply_markup=reply_markup
    )
    return AGREGAR_CALIFICACION

async def handle_calificacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar ingreso de calificación"""
    volver = await check_volver_menu(update, context)
    if volver is not None:
        return volver
    
    text = update.message.text
    user_id = update.message.from_user.id
    
    # Si está esperando una calificación numérica
    if context.user_data.get('esperando_calificacion'):
        try:
            calificacion = float(text.replace(',', '.'))
            
            if not (0 <= calificacion <= 100):
                await update.message.reply_text(
                    "❌ La calificación debe estar entre 0 y 100. Intenta de nuevo:",
                    reply_markup=back_keyboard()
                )
                return AGREGAR_CALIFICACION
            
            # Obtener datos de la materia
            materia_data = context.user_data.get('materia_actual')
            if not materia_data:
                await update.message.reply_text(
                    "❌ Error: no se encontró la materia.",
                    reply_markup=main_keyboard()
                )
                return MENU
            
            materia_id = materia_data['id']
            materia_nombre = materia_data['nombre']
            
            # Actualizar calificación
            actualizar_calificacion_db(materia_id, user_id, calificacion)
            
            status = "✅ Aprobada" if calificacion >= 60 else "❌ Reprobada"
            
            await update.message.reply_text(
                f"✅ **Calificación registrada!**\n\n"
                f"📚 Materia: {materia_nombre}\n"
                f"🎯 Calificación: {calificacion}/100\n"
                f"📈 Estado: {status}",
                reply_markup=main_keyboard()
            )
            
            # Limpiar datos temporales
            context.user_data['esperando_calificacion'] = False
            context.user_data['materia_actual'] = None
            
            return MENU
            
        except ValueError:
            await update.message.reply_text(
                "❌ Por favor ingresa un número válido para la calificación (0-100):",
                reply_markup=back_keyboard()
            )
            return AGREGAR_CALIFICACION
    
    else:
        # Selección de materia para calificar
        if text.startswith("Calificar:"):
            materia_data = context.user_data['materias_calificar'].get(text)
            if materia_data:
                context.user_data['materia_actual'] = materia_data
                context.user_data['esperando_calificacion'] = True
                
                await update.message.reply_text(
                    f"📝 **Calificando: {materia_data['nombre']}**\n\n"
                    f"💡 Por favor ingresa la calificación (0-100):",
                    reply_markup=back_keyboard()
                )
                return AGREGAR_CALIFICACION
        else:
            await update.message.reply_text(
                "❌ Por favor selecciona una materia del teclado:",
                reply_markup=ReplyKeyboardMarkup(
                    [[m] for m in context.user_data['materias_calificar'].keys()] + [["🔙 Menú Principal"]],
                    resize_keyboard=True
                )
            )
            return AGREGAR_CALIFICACION

# --- FLUJO ELIMINAR MATERIA ---
async def iniciar_eliminacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Iniciar proceso de eliminación"""
    user_id = update.message.from_user.id
    materias = obtener_materias_usuario(user_id)
    
    if not materias:
        await update.message.reply_text(
            "📭 No tienes materias para eliminar.",
            reply_markup=main_keyboard()
        )
        return MENU
    
    # Crear teclado con materias
    keyboard = []
    materias_dict = {}
    
    for id, semestre, nombre, _, _, _, _ in materias:
        keyboard.append([f"Eliminar: {nombre} (S{semestre})"])
        materias_dict[f"Eliminar: {nombre} (S{semestre})"] = id
    keyboard.append(["🔙 Menú Principal"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data['materias_eliminar'] = materias_dict
    
    await update.message.reply_text(
        "🗑️ **Selecciona la materia a eliminar:**",
        reply_markup=reply_markup
    )
    return CONFIRMAR_ELIMINAR

async def handle_confirmar_eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar confirmación de eliminación"""
    volver = await check_volver_menu(update, context)
    if volver is not None:
        return volver
    
    text = update.message.text
    user_id = update.message.from_user.id
    
    if text.startswith("Eliminar:"):
        try:
            # Extraer ID de la materia
            materia_id = context.user_data['materias_eliminar'][text]
            
            # Eliminar de la base de datos
            if eliminar_materia_db(materia_id, user_id):
                await update.message.reply_text(
                    "✅ Materia eliminada exitosamente.",
                    reply_markup=main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ No se pudo eliminar la materia.",
                    reply_markup=main_keyboard()
                )
            
            return MENU
            
        except Exception as e:
            await update.message.reply_text(
                "❌ Error al eliminar la materia.",
                reply_markup=main_keyboard()
            )
            return MENU
    else:
        await update.message.reply_text(
            "❌ Opción no reconocida.",
            reply_markup=main_keyboard()
        )
        return MENU

# --- FLUJO AVANCE ACADÉMICO ---
async def mostrar_avance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar avance académico"""
    user_id = update.message.from_user.id
    
    # Total créditos del plan
    total_creditos_plan = sum(materia['creditos'] for semestre in PLAN_ESTUDIOS.values() for materia in semestre)
    
    # Créditos cursados
    materias = obtener_materias_usuario(user_id)
    creditos_cursados = sum(creditos for _, _, _, creditos, _, estado, _ in materias if estado == "aprobada")
    
    # Calcular porcentaje
    porcentaje = (creditos_cursados / total_creditos_plan) * 100 if total_creditos_plan > 0 else 0
    
    response = f"📊 **AVANCE ACADÉMICO - UPSLP**\n\n"
    response += f"🎯 **Progreso general:** {porcentaje:.1f}%\n"
    response += f"📚 Créditos cursados: {creditos_cursados}/{total_creditos_plan}\n\n"
    
    # Avance por semestre
    response += "**Avance por semestre:**\n"
    for semestre in range(1, 10):
        materias_semestre = len(PLAN_ESTUDIOS.get(semestre, []))
        materias_cursadas = len([m for m in materias if m[1] == semestre])
        avance_semestre = (materias_cursadas / materias_semestre) * 100 if materias_semestre > 0 else 0
        response += f"• {semestre}° Semestre: {materias_cursadas}/{materias_semestre} materias ({avance_semestre:.1f}%)\n"
    
    # Barra de progreso
    barras = int(porcentaje / 10)
    barra_progreso = "[" + "█" * barras + "░" * (10 - barras) + "]"
    response += f"\n{barra_progreso} {porcentaje:.1f}%"
    
    await update.message.reply_text(response, reply_markup=main_keyboard())

# --- FLUJO ESTADÍSTICAS ---
async def mostrar_estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar estadísticas académicas"""
    user_id = update.message.from_user.id
    materias = obtener_materias_usuario(user_id)
    
    total_materias = len(materias)
    total_creditos = sum(creditos for _, _, _, creditos, _, _, _ in materias)
    
    materias_calificadas = len([m for m in materias if m[6] is not None])
    materias_aprobadas = len([m for m in materias if m[6] is not None and m[6] >= 60])
    
    # Calcular promedio
    calificaciones = [m[6] for m in materias if m[6] is not None]
    promedio = sum(calificaciones) / len(calificaciones) if calificaciones else 0
    
    # Distribución por tipo
    tipos = {}
    for _, _, _, _, tipo, _, _ in materias:
        tipos[tipo] = tipos.get(tipo, 0) + 1
    
    response = "📈 **ESTADÍSTICAS ACADÉMICAS**\n\n"
    response += f"📚 Total materias: {total_materias}\n"
    response += f"🎯 Total créditos: {total_creditos}\n"
    response += f"⭐ Promedio general: {promedio:.2f}/100\n"
    response += f"✅ Materias aprobadas: {materias_aprobadas}\n"
    response += f"📝 Materias calificadas: {materias_calificadas}\n\n"
    
    response += "**Distribución por tipo:**\n"
    for tipo, count in tipos.items():
        response += f"• {tipo}: {count} materias\n"
    
    await update.message.reply_text(response, reply_markup=main_keyboard())

# --- FLUJO PLAN DE ESTUDIOS ---
async def mostrar_plan_estudios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostrar plan de estudios completo (sin créditos)"""
    response = "📖 **PLAN DE ESTUDIOS - UPSLP**\n\n"
    
    for semestre, materias in PLAN_ESTUDIOS.items():
        response += f"🎯 **{semestre}° SEMESTRE**\n"
        for materia in materias:
            response += f"📚 {materia['nombre']} - {materia['tipo']}\n"  # Sin créditos
        response += "\n"
    
    await update.message.reply_text(response, reply_markup=main_keyboard())

# --- FUNCIONES AUXILIARES ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ¡Hasta luego!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    try:
        if update and update.message:
            await update.message.reply_text("⚠️ Error. Escribe 'menu' para volver", reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"Error en error_handler: {e}")

# --- CONFIGURACIÓN WEBHOOK PARA RENDER ---
def setup_application():
    """Configurar la aplicación de Telegram"""
    application = Application.builder().token(TOKEN).build()
    
    # Conversación principal
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)],
            SELECCION_SEMESTRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_seleccion_semestre)],
            SELECCION_MATERIAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_seleccion_materias)],
            AGREGAR_CALIFICACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_calificacion)],
            CONFIRMAR_ELIMINAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmar_eliminar)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    return application

# Crear aplicación de Telegram
application = setup_application()

# Crear aplicación Flask
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({
        'status': 'live', 
        'service': 'UPSLP Academic Bot',
        'webhook_url': f'{WEBAPP_URL}/webhook'
    })

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint para recibir updates de Telegram"""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put(update)
        return 'ok'
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        return 'error', 400

@flask_app.route('/set-webhook')
def set_webhook():
    """Configurar webhook manualmente"""
    try:
        webhook_url = f"{WEBAPP_URL}/webhook"
        result = application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        )
        return jsonify({
            'status': 'success',
            'webhook_url': webhook_url,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error configurando webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@flask_app.route('/webhook-info')
def webhook_info():
    """Obtener información del webhook"""
    try:
        info = application.bot.get_webhook_info()
        return jsonify({
            'url': info.url,
            'has_custom_certificate': info.has_custom_certificate,
            'pending_update_count': info.pending_update_count,
            'last_error_date': info.last_error_date,
            'last_error_message': info.last_error_message,
            'max_connections': info.max_connections,
            'allowed_updates': info.allowed_updates
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def main():
    """Función principal - SOLO para desarrollo local"""
    print("🚀 Iniciando Bot Académico UPSLP (MODO LOCAL)...")
    
    if not TOKEN:
        print("❌ ERROR: BOT_TOKEN no encontrado")
        return
    
    print(f"✅ Token cargado: {TOKEN[:10]}...")
    
    # SOLO para desarrollo local usar polling
    print("🔧 Iniciando en modo polling (solo para desarrollo local)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Configuración para Render - esto se ejecuta al importar el módulo
def setup_webhook():
    """Configurar webhook solo cuando el servicio esté corriendo en Render"""
    try:
        # Pequeña espera para asegurar que el servicio esté listo
        time.sleep(2)
        
        webhook_url = f"{WEBAPP_URL}/webhook"
        logger.info(f"🔗 Configurando webhook: {webhook_url}")
        
        application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        logger.info("✅ Webhook configurado exitosamente!")
        
    except Exception as e:
        logger.error(f"❌ Error configurando webhook: {e}")

# Configurar webhook automáticamente al iniciar en Render
if os.environ.get('RENDER', False) or os.environ.get('PORT'):
    logger.info("🌐 Entorno Render detectado, configurando webhook...")
    # Usar un pequeño retraso para asegurar que el servicio esté listo
    import threading
    thread = threading.Timer(5.0, setup_webhook)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    # Esto solo se ejecutará en desarrollo local
    main()