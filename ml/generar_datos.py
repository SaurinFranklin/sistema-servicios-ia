"""
Generador de datos sintéticos para el sistema de servicios técnicos.
Ejecutar:  python ../ml/training/generar_datos.py   (desde backend, con venv activo)

OJO: borra y recrea las tablas cada vez que se ejecuta.
"""
import csv
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

# --- Rutas: así el script funciona sin importar desde dónde lo ejecutes ---
RAIZ = Path(__file__).resolve().parents[2]
sys.path.append(str(RAIZ / "backend")) 
os.chdir(RAIZ / "backend")

from database import Base, engine, SessionLocal
from models import Cliente, Equipo, Tecnico, Orden, HistorialEstado, Repuesto, OrdenRepuesto
import catalogo

# --- Parámetros que puedes cambiar ---
SEMILLA = 42           
N_CLIENTES = 1500
N_ORDENES = 4000
DIAS_HISTORIAL = 540 

# Qué tan frecuente es cada falla (más peso = más común)
PESO_FALLA = {
    "bateria": 8, "pantalla": 12, "placa_madre": 6, "fuente_poder": 5,
    "disco_duro": 10, "software": 22, "sobrecalentamiento": 9,
    "teclado_touchpad": 6, "atasco_papel": 8, "cabezal_tinta": 9, "fusor_laser": 5,
}

# Qué especialidad de técnico corresponde a cada falla
ESPECIALIDAD_FALLA = {
    "bateria": "hardware", "pantalla": "hardware", "placa_madre": "hardware",
    "fuente_poder": "hardware", "disco_duro": "hardware", "software": "software",
    "sobrecalentamiento": "hardware", "teclado_touchpad": "hardware",
    "atasco_papel": "impresoras", "cabezal_tinta": "impresoras", "fusor_laser": "impresoras",
}

# Etapas del flujo y en qué fracción del tiempo total ocurre cada una
ETAPAS = [("recibido", 0.0), ("diagnostico", 0.10), ("en_reparacion", 0.25),
          ("listo", 0.95), ("entregado", 1.0)]

PREFIJOS = ["hola, ", "buenas, ", "mi equipo: ", "urgente: ", "oiga, ", "buenos dias, "]
SUFIJOS = [" desde ayer", " hace una semana", " desde hace dias", " por favor ayuda",
           " y lo necesito pronto", " ya paso antes"]
FRASES_VAGAS = ["no funciona bien", "tiene un problema pero no se que es",
                "falla de repente", "no anda como antes"]


# ---------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------
def agregar_error(texto):
    """Simula un error de tipeo en una palabra: borra, intercambia o duplica una letra."""
    palabras = texto.split()
    candidatas = [i for i, p in enumerate(palabras) if len(p) > 4]
    if not candidatas:
        return texto
    i = random.choice(candidatas)
    p = palabras[i]
    pos = random.randint(1, len(p) - 2)
    tipo = random.choice(["borrar", "intercambiar", "duplicar"])
    if tipo == "borrar":
        p = p[:pos] + p[pos + 1:]
    elif tipo == "intercambiar":
        p = p[:pos] + p[pos + 1] + p[pos] + p[pos + 2:]
    else:
        p = p[:pos] + p[pos] + p[pos:]
    palabras[i] = p
    return " ".join(palabras)


def generar_descripcion(info_falla):
    """Arma lo que escribiría el cliente: frase base + variaciones + errores."""
    if random.random() < 0.05:
        texto = random.choice(FRASES_VAGAS)
    else:
        texto = random.choice(info_falla["frases"])
    if random.random() < 0.25:
        texto = random.choice(PREFIJOS) + texto
    if random.random() < 0.25:
        texto += random.choice(SUFIJOS)
    if random.random() < 0.35:
        texto = agregar_error(texto)
    if random.random() < 0.05:
        texto = texto.upper()
    return texto


def factor_experiencia(anios):
    """Técnicos con menos experiencia tardan más."""
    if anios <= 1:
        return 1.30
    if anios <= 3:
        return 1.15
    if anios <= 6:
        return 1.00
    return 0.90


def elegir_repuestos(nombre_falla, info_falla):
    """Decide qué repuestos se usan en esta orden."""
    lista = info_falla["repuestos"]
    if not lista:
        return []
    if nombre_falla == "disco_duro":
        return [random.choice(lista)]
    return [lista[0]] + [r for r in lista[1:] if random.random() < 0.5]


def ajustar_prioridad(base):
    """El 15% de las veces la prioridad real difiere de la típica."""
    niveles = ["baja", "media", "alta"]
    if random.random() < 0.15:
        i = niveles.index(base) + random.choice([-1, 1])
        return niveles[max(0, min(2, i))]
    return base


# ---------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------
def main():
    random.seed(SEMILLA)
    Faker.seed(SEMILLA)
    fake = Faker("es_ES")
    ahora = datetime.now()

    # Reiniciamos la base de datos
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as s:
        # 1) Técnicos y repuestos (vienen del catálogo)
        tecnicos = [Tecnico(nombre=n, especialidad=e, anios_experiencia=a)
                    for n, e, a in catalogo.TECNICOS]
        repuestos = {n: Repuesto(nombre=n, categoria=c, precio=p, stock=st)
                     for n, c, p, st in catalogo.REPUESTOS}
        precios = {n: p for n, c, p, st in catalogo.REPUESTOS}

        # 2) Clientes con DNI único
        clientes, dnis = [], set()
        while len(clientes) < N_CLIENTES:
            dni = str(random.randint(10_000_000, 79_999_999))
            if dni in dnis:
                continue
            dnis.add(dni)
            clientes.append(Cliente(
                nombre=fake.name(), dni=dni,
                telefono="9" + str(random.randint(10_000_000, 99_999_999)),
                email=fake.email() if random.random() < 0.7 else None,
            ))

        s.add_all(tecnicos)
        s.add_all(repuestos.values())
        s.add_all(clientes)
        s.flush()

        # 3) Órdenes
        nombres_falla = list(PESO_FALLA)
        pesos = [PESO_FALLA[f] for f in nombres_falla]
        pares = []

        for _ in range(N_ORDENES):
            nombre_falla = random.choices(nombres_falla, weights=pesos)[0]
            info = catalogo.FALLAS[nombre_falla]

            # Equipo
            tipo = random.choice(info["tipos"])
            marca = random.choice(list(catalogo.MARCAS[tipo]))
            factor_marca, modelos = catalogo.MARCAS[tipo][marca]
            equipo = Equipo(
                cliente=random.choice(clientes), tipo=tipo, marca=marca,
                modelo=random.choice(modelos),
                serie=fake.bothify("??#######").upper(),
            )

            # Técnico: 80% del tiempo uno con la especialidad correcta
            especialidad = ESPECIALIDAD_FALLA[nombre_falla]
            aptos = [t for t in tecnicos if t.especialidad == especialidad]
            tecnico = random.choice(aptos) if random.random() < 0.8 else random.choice(tecnicos)

            # --- Regla de TIEMPO ---
            dmin, dmax = info["dias"]
            tiempo = random.uniform(dmin, dmax)
            tiempo *= factor_experiencia(tecnico.anios_experiencia)
            if tecnico.especialidad != especialidad:
                tiempo *= 1.25
            if marca == "Apple":
                tiempo *= 1.20
            tiempo *= random.gauss(1.0, 0.12)
            if random.random() < 0.06:
                tiempo *= random.uniform(1.4, 2.2)
            tiempo = round(max(0.5, tiempo), 1)

            # --- Regla de COSTO ---
            usados = elegir_repuestos(nombre_falla, info)
            costo = info["mano_obra"] + sum(precios[r] for r in usados)
            costo *= factor_marca
            costo *= random.gauss(1.0, 0.08)
            if random.random() < 0.04:
                costo *= random.uniform(1.2, 1.6)
            costo = round(max(10, costo), 2)

            # Fechas y estado
            ingreso = ahora - timedelta(days=random.uniform(0, DIAS_HISTORIAL))
            entrega = ingreso + timedelta(days=tiempo)
            terminada = entrega <= ahora

            # Historial: solo las etapas que ya ocurrieron
            etapas_hechas = [(e, ingreso + timedelta(days=tiempo * f))
                             for e, f in ETAPAS if ingreso + timedelta(days=tiempo * f) <= ahora]

            orden = Orden(
                equipo=equipo, tecnico=tecnico,
                descripcion_falla=generar_descripcion(info),
                categoria_falla=nombre_falla,
                prioridad=ajustar_prioridad(info["prioridad"]),
                estado=etapas_hechas[-1][0],
                fecha_ingreso=ingreso,
                fecha_entrega=entrega if terminada else None,
                tiempo_real_dias=tiempo if terminada else None,
                costo_real=costo if terminada else None,
            )
            for estado, fecha in etapas_hechas:
                HistorialEstado(orden=orden, estado=estado, fecha=fecha)
            for r in usados:
                OrdenRepuesto(orden=orden, repuesto=repuestos[r], cantidad=1)

            s.add(orden)
            pares.append((orden, equipo, tecnico, usados))

        s.flush()

        # 4) Exportar CSV (para entrenar los modelos)
        ruta_csv = RAIZ / "ml" / "data" / "ordenes.csv"
        columnas = ["orden_id", "tipo_equipo", "marca", "modelo", "tecnico",
                    "especialidad_tecnico", "anios_experiencia", "descripcion_falla",
                    "categoria_falla", "prioridad", "repuestos", "num_repuestos",
                    "fecha_ingreso", "estado", "tiempo_real_dias", "costo_real"]
        with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=columnas)
            w.writeheader()
            for o, eq, tec, usados in pares:
                w.writerow({
                    "orden_id": o.id, "tipo_equipo": eq.tipo, "marca": eq.marca,
                    "modelo": eq.modelo, "tecnico": tec.nombre,
                    "especialidad_tecnico": tec.especialidad,
                    "anios_experiencia": tec.anios_experiencia,
                    "descripcion_falla": o.descripcion_falla,
                    "categoria_falla": o.categoria_falla, "prioridad": o.prioridad,
                    "repuestos": "|".join(usados), "num_repuestos": len(usados),
                    "fecha_ingreso": o.fecha_ingreso.strftime("%Y-%m-%d %H:%M"),
                    "estado": o.estado, "tiempo_real_dias": o.tiempo_real_dias,
                    "costo_real": o.costo_real,
                })

        s.commit()

        # 5) Resumen en pantalla
        print(f"Clientes: {len(clientes)} | Órdenes: {len(pares)}")
        print(f"CSV guardado en: {ruta_csv}\n")
        print(f"{'falla':<20}{'órdenes':>8}{'días prom.':>12}{'costo prom.':>13}")
        for nombre in nombres_falla:
            terminadas = [o for o, *_ in pares
                          if o.categoria_falla == nombre and o.tiempo_real_dias is not None]
            total = sum(1 for o, *_ in pares if o.categoria_falla == nombre)
            if terminadas:
                d = sum(o.tiempo_real_dias for o in terminadas) / len(terminadas)
                c = sum(o.costo_real for o in terminadas) / len(terminadas)
                print(f"{nombre:<20}{total:>8}{d:>12.1f}{c:>13.1f}")


if __name__ == "__main__":
    main()