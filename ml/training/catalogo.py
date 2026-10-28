"""
Catálogo del negocio: aquí viven las reglas que usará el generador de datos.
Si algún día tienes datos reales, esta información la reemplazan ellos.
"""

# ---------------------------------------------------------------
# 1. FALLAS
# Cada falla tiene:
#   - tipos: en qué equipos puede ocurrir
#   - dias: tiempo base de reparación (mínimo, máximo)
#   - mano_obra: costo base de la mano de obra en soles
#   - repuestos: repuestos que suele necesitar
#   - prioridad: qué tan urgente suele ser
#   - frases: cómo la describiría un cliente
# ---------------------------------------------------------------
FALLAS = {
    "bateria": {
        "tipos": ["laptop"],
        "dias": (1, 2),
        "mano_obra": 30,
        "repuestos": ["Batería de laptop"],
        "prioridad": "media",
        "frases": [
            "la laptop se apaga sola cuando la desconecto",
            "la batería dura muy poco, como 10 minutos",
            "no carga aunque este conectada al cargador",
            "la bateria esta hinchada y levanta el teclado",
            "marca 0% de carga y se apaga de golpe",
        ],
    },
    "pantalla": {
        "tipos": ["laptop", "pc"],
        "dias": (2, 5),
        "mano_obra": 50,
        "repuestos": ["Pantalla LCD", "Cable flex de pantalla"],
        "prioridad": "alta",
        "frases": [
            "la pantalla esta rota por un golpe",
            "se ven lineas de colores en la pantalla",
            "la pantalla se ve negra pero la compu prende",
            "tiene una mancha oscura que crece en la pantalla",
            "la imagen parpadea y a veces se va",
        ],
    },
    "placa_madre": {
        "tipos": ["laptop", "pc"],
        "dias": (5, 12),
        "mano_obra": 120,
        "repuestos": ["Placa madre", "Pasta térmica"],
        "prioridad": "alta",
        "frases": [
            "no enciende para nada y huele a quemado",
            "se mojo con agua y ya no prende",
            "prende unos segundos y se apaga, no da imagen",
            "no da video y los ventiladores giran fuerte",
            "se cayo la luz y desde entonces no responde",
        ],
    },
    "fuente_poder": {
        "tipos": ["pc"],
        "dias": (1, 3),
        "mano_obra": 40,
        "repuestos": ["Fuente de poder"],
        "prioridad": "alta",
        "frases": [
            "la pc no enciende, no hace ningun ruido",
            "se apaga sola de repente mientras trabajo",
            "hizo un chispazo y se apago todo",
            "huele a plastico quemado cuando la prendo",
        ],
    },
    "disco_duro": {
        "tipos": ["laptop", "pc"],
        "dias": (2, 4),
        "mano_obra": 60,
        "repuestos": ["Disco SSD", "Disco duro HDD"],
        "prioridad": "alta",
        "frases": [
            "hace ruidos raros de clic y esta muy lenta",
            "dice que no encuentra el sistema operativo",
            "se queda en pantalla negra con un mensaje de disco",
            "perdi mis archivos y no abre carpetas",
            "tarda mas de 10 minutos en prender",
        ],
    },
    "software": {
        "tipos": ["laptop", "pc"],
        "dias": (1, 2),
        "mano_obra": 45,
        "repuestos": [],
        "prioridad": "baja",
        "frases": [
            "esta muy lenta y se traba todo",
            "creo que tiene virus, salen ventanas raras",
            "necesito formatear e instalar windows",
            "no me abre el office ni el navegador",
            "salio pantalla azul con un error",
        ],
    },
    "sobrecalentamiento": {
        "tipos": ["laptop", "pc"],
        "dias": (1, 3),
        "mano_obra": 40,
        "repuestos": ["Ventilador", "Pasta térmica"],
        "prioridad": "media",
        "frases": [
            "se calienta muchisimo y el ventilador suena fuerte",
            "se apaga sola cuando juego o abro programas pesados",
            "esta muy caliente y hace ruido como de avion",
            "el ventilador no gira y se apaga por calor",
        ],
    },
    "teclado_touchpad": {
        "tipos": ["laptop"],
        "dias": (1, 3),
        "mano_obra": 35,
        "repuestos": ["Teclado de laptop"],
        "prioridad": "baja",
        "frases": [
            "varias teclas no responden",
            "se me cayo cafe en el teclado",
            "el mouse touchpad no funciona o se mueve solo",
            "algunas letras escriben dos veces",
        ],
    },
    "atasco_papel": {
        "tipos": ["impresora"],
        "dias": (1, 2),
        "mano_obra": 25,
        "repuestos": ["Rodillo de arrastre"],
        "prioridad": "media",
        "frases": [
            "se atasca el papel y sale arrugado",
            "jala varias hojas a la vez",
            "dice atasco de papel pero no veo nada atascado",
            "no agarra el papel de la bandeja",
        ],
    },
    "cabezal_tinta": {
        "tipos": ["impresora"],
        "dias": (2, 4),
        "mano_obra": 50,
        "repuestos": ["Cabezal de impresión", "Kit de tinta"],
        "prioridad": "media",
        "frases": [
            "imprime con rayas o faltan colores",
            "las hojas salen en blanco aunque tiene tinta",
            "salen manchas de tinta en las hojas",
            "limpie los cabezales varias veces y sigue igual",
        ],
    },
    "fusor_laser": {
        "tipos": ["impresora"],
        "dias": (3, 6),
        "mano_obra": 70,
        "repuestos": ["Fusor", "Tóner"],
        "prioridad": "media",
        "frases": [
            "el toner se borra al tocar la hoja impresa",
            "sale con un fondo gris y manchas negras",
            "hace un ruido fuerte y sale humo leve",
            "las hojas salen muy calientes y arrugadas",
        ],
    },
}

# ---------------------------------------------------------------
# 2. REPUESTOS (nombre, categoría, precio en soles, stock inicial)
# ---------------------------------------------------------------
REPUESTOS = [
    ("Batería de laptop", "energia", 120, 25),
    ("Pantalla LCD", "pantalla", 280, 15),
    ("Cable flex de pantalla", "pantalla", 45, 30),
    ("Placa madre", "placa", 420, 8),
    ("Pasta térmica", "consumible", 15, 60),
    ("Fuente de poder", "energia", 130, 20),
    ("Disco SSD", "almacenamiento", 160, 25),
    ("Disco duro HDD", "almacenamiento", 140, 15),
    ("Ventilador", "refrigeracion", 55, 30),
    ("Teclado de laptop", "periferico", 70, 20),
    ("Rodillo de arrastre", "impresora", 40, 25),
    ("Cabezal de impresión", "impresora", 180, 10),
    ("Kit de tinta", "consumible", 60, 40),
    ("Fusor", "impresora", 250, 6),
    ("Tóner", "consumible", 95, 30),
]

# ---------------------------------------------------------------
# 3. MARCAS Y MODELOS por tipo de equipo
# El factor multiplica el costo: una marca "premium" cuesta más.
# ---------------------------------------------------------------
MARCAS = {
    "laptop": {
        "HP": (1.0, ["Pavilion 15", "250 G8", "Envy 13"]),
        "Lenovo": (1.0, ["IdeaPad 3", "ThinkPad E14", "Legion 5"]),
        "Dell": (1.1, ["Inspiron 15", "Latitude 5420", "XPS 13"]),
        "Asus": (1.0, ["VivoBook 15", "TUF Gaming F15"]),
        "Acer": (0.9, ["Aspire 5", "Nitro 5"]),
        "Apple": (1.8, ["MacBook Air M1", "MacBook Pro 13"]),
    },
    "pc": {
        "Ensamblada": (1.0, ["Torre Gamer", "Torre Oficina"]),
        "HP": (1.0, ["ProDesk 400", "Pavilion Desktop"]),
        "Dell": (1.1, ["OptiPlex 3080", "Vostro 3888"]),
        "Lenovo": (1.0, ["ThinkCentre M70", "IdeaCentre 3"]),
    },
    "impresora": {
        "Epson": (1.0, ["L3150", "L805", "L4260"]),
        "HP": (1.0, ["LaserJet Pro M15", "DeskJet 2775"]),
        "Canon": (0.95, ["Pixma G3110", "imageCLASS MF445"]),
        "Brother": (1.0, ["DCP-T520W", "HL-L2370DW"]),
    },
}

# ---------------------------------------------------------------
# 4. TÉCNICOS (nombre, especialidad, años de experiencia)
# A más experiencia, menos tiempo tarda (lo aplicamos en el generador)
# ---------------------------------------------------------------
TECNICOS = [
    ("Carlos Mendoza", "hardware", 8),
    ("Lucía Torres", "hardware", 3),
    ("Jorge Ramírez", "software", 5),
    ("Ana Castillo", "impresoras", 6),
    ("Miguel Salazar", "hardware", 1),
    ("Rosa Paredes", "impresoras", 2),
]