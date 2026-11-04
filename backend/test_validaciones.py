import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

import main
from database import Base, obtener_db
from models import Tecnico


class PruebasValidaciones(unittest.TestCase):
    def setUp(self):
        # Cada prueba utiliza una base nueva que existe solo en memoria.
        motor = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(motor.dispose)

        Base.metadata.create_all(motor)
        SesionPrueba = sessionmaker(bind=motor)
        self.SesionPrueba = SesionPrueba

        def obtener_db_prueba():
            with SesionPrueba() as sesion:
                yield sesion

        # Sustituimos la conexión únicamente en este proceso de pruebas.
        anteriores = main.app.dependency_overrides.copy()
        self.addCleanup(
            setattr,
            main.app,
            "dependency_overrides",
            anteriores,
        )
        main.app.dependency_overrides[obtener_db] = obtener_db_prueba

        # Estas pruebas verifican reglas del sistema, no los modelos de IA.
        self.enterContext(patch("main.cargar_modelos"))
        self.api = self.enterContext(TestClient(main.app))

        with SesionPrueba() as sesion:
            tecnico = Tecnico(
                nombre="Técnico de prueba",
                especialidad="hardware",
                anios_experiencia=5,
            )
            sesion.add(tecnico)
            sesion.commit()
            sesion.refresh(tecnico)
            self.tecnico_id = tecnico.id

        self.datos_cliente = {
            "nombre": "Cliente automatizado",
            "dni": "90000001",
            "telefono": "900000001",
            "email": None,
        }

        self.cliente = self.peticion(
            "POST", "/clientes", 201, json=self.datos_cliente
        )

        self.equipo = self.peticion(
            "POST",
            "/equipos",
            201,
            json={
                "cliente_id": self.cliente["id"],
                "tipo": "laptop",
                "marca": "Lenovo",
                "modelo": "Equipo de prueba",
                "serie": "TEST-001",
            },
        )

        self.orden = self.peticion(
            "POST",
            "/ordenes",
            201,
            json={
                "equipo_id": self.equipo["id"],
                "descripcion_falla": "Varias teclas no responden.",
                "prioridad": "media",
            },
        )

        self.ruta = f"/ordenes/{self.orden['id']}"

    def peticion(self, metodo, ruta, esperado, **opciones):
        respuesta = self.api.request(metodo, ruta, **opciones)
        self.assertEqual(
            respuesta.status_code,
            esperado,
            f"{metodo} {ruta}: {respuesta.text}",
        )
        return respuesta.json()

    def detalle(self):
        return self.peticion("GET", f"{self.ruta}/detalle", 200)

    def preparar_entrega(self):
        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "teclado_touchpad",
            },
        )

        self.peticion(
            "POST",
            f"{self.ruta}/observaciones",
            201,
            json={"texto": "El teclado USB funciona correctamente."},
        )

        for estado in ("en_reparacion", "listo", "entregado"):
            resultado = self.peticion(
                "PATCH",
                f"{self.ruta}/estado",
                200,
                json={"estado": estado},
            )
            self.assertEqual(resultado["estado"], estado)

        self.peticion(
            "PATCH",
            f"{self.ruta}/costo-real",
            200,
            json={"costo_real": 130},
        )

        datos = self.detalle()
        self.assertIsNotNone(datos["orden"]["fecha_entrega"])
        self.assertGreaterEqual(datos["orden"]["tiempo_real_dias"], 0)
        self.assertEqual(
            [evento["estado"] for evento in datos["historial"]],
            ["recibido", "diagnostico", "en_reparacion", "listo", "entregado"],
        )

    def test_descripcion_vacia(self):
        antes = self.peticion("GET", "/ordenes", 200)

        error = self.peticion(
            "POST",
            "/ordenes",
            422,
            json={
                "equipo_id": self.equipo["id"],
                "descripcion_falla": "   ",
                "prioridad": "media",
            },
        )

        self.assertTrue(any(
            item["loc"] == ["body", "descripcion_falla"]
            for item in error["detail"]
        ))
        self.assertEqual(self.peticion("GET", "/ordenes", 200), antes)

    def test_dni_duplicado(self):
        datos = dict(self.datos_cliente, nombre="Nombre duplicado")

        error = self.peticion("POST", "/clientes", 409, json=datos)

        self.assertEqual(
            error["detail"],
            "Ya existe un cliente con ese DNI.",
        )

        clientes = self.peticion("GET", "/clientes", 200)
        self.assertEqual(len(clientes), 1)
        self.assertEqual(clientes[0]["nombre"], "Cliente automatizado")

    def test_orden_inexistente(self):
        error = self.peticion("GET", "/ordenes/999999/detalle", 404)
        self.assertEqual(error["detail"], "Orden no encontrada.")

    def test_no_retroceder_desde_entregado(self):
        self.preparar_entrega()
        antes = self.detalle()

        error = self.peticion(
            "PATCH",
            f"{self.ruta}/estado",
            409,
            json={"estado": "en_reparacion"},
        )

        self.assertEqual(
            error["detail"],
            "No se puede pasar de 'entregado' a 'en_reparacion'.",
        )
        self.assertEqual(self.detalle(), antes)

    def test_costo_negativo(self):
        self.preparar_entrega()
        antes = self.detalle()

        error = self.peticion(
            "PATCH",
            f"{self.ruta}/costo-real",
            422,
            json={"costo_real": -10},
        )

        self.assertTrue(any(
            item["loc"] == ["body", "costo_real"]
            for item in error["detail"]
        ))
        self.assertEqual(self.detalle(), antes)

    def test_observacion_despues_de_entrega(self):
        self.preparar_entrega()
        antes = self.detalle()

        error = self.peticion(
            "POST",
            f"{self.ruta}/observaciones",
            409,
            json={"texto": "Esta observación debe rechazarse."},
        )

        self.assertIn(
            "Las observaciones se registran durante",
            error["detail"],
        )
        self.assertEqual(self.detalle(), antes)

    def test_repetir_entrega_conserva_datos(self):
        self.preparar_entrega()
        antes = self.detalle()

        self.peticion(
            "PATCH",
            f"{self.ruta}/estado",
            200,
            json={"estado": "entregado"},
        )

        self.assertEqual(self.detalle(), antes)
    def preparar_estimacion(self):
        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "teclado_touchpad",
            },
        )

        resultado_simulado = {
            "tiempo_estimado_dias": 2.5,
            "costo_estimado": 200.0,
            "modelo_tiempo_sha256": "a" * 64,
            "modelo_costo_sha256": "b" * 64,
        }

        with patch(
            "ordenes.estimar_servicio",
            return_value=resultado_simulado,
        ) as estimador:
            self.peticion(
                "POST",
                f"{self.ruta}/estimacion",
                200,
                json={"num_repuestos": 1},
            )

            # Verificamos los datos enviados al estimador.
            estimador.assert_called_once_with(
                tipo_equipo="laptop",
                marca="Lenovo",
                categoria_falla="teclado_touchpad",
                tecnico="Técnico de prueba",
                anios_experiencia=5,
                num_repuestos=1,
                prioridad="media",
            )

        # Otra consulta comprueba que los valores quedaron guardados.
        orden = self.detalle()["orden"]
        self.assertEqual(orden["tiempo_estimado_dias"], 2.5)
        self.assertEqual(orden["costo_estimado"], 200.0)

    def test_estimacion_se_guarda(self):
        self.preparar_estimacion()

        datos = self.detalle()

        self.assertEqual(datos["orden"]["estado"], "diagnostico")
        self.assertIsNone(datos["orden"]["tiempo_real_dias"])
        self.assertIsNone(datos["orden"]["costo_real"])
        self.assertEqual(
            [evento["estado"] for evento in datos["historial"]],
            ["recibido", "diagnostico"],
        )

    def test_cambiar_categoria_invalida_estimacion(self):
        self.preparar_estimacion()

        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "software",
            },
        )

        orden = self.detalle()["orden"]
        self.assertEqual(orden["categoria_falla"], "software")
        self.assertEqual(orden["tecnico_id"], self.tecnico_id)
        self.assertIsNone(orden["tiempo_estimado_dias"])
        self.assertIsNone(orden["costo_estimado"])

    def test_cambiar_tecnico_invalida_estimacion(self):
        self.preparar_estimacion()

        with self.SesionPrueba() as sesion:
            otro_tecnico = Tecnico(
                nombre="Segundo técnico de prueba",
                especialidad="hardware",
                anios_experiencia=2,
            )
            sesion.add(otro_tecnico)
            sesion.commit()
            sesion.refresh(otro_tecnico)
            otro_id = otro_tecnico.id

        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": otro_id,
                "categoria_falla": "teclado_touchpad",
            },
        )

        orden = self.detalle()["orden"]
        self.assertEqual(orden["tecnico_id"], otro_id)
        self.assertEqual(orden["categoria_falla"], "teclado_touchpad")
        self.assertIsNone(orden["tiempo_estimado_dias"])
        self.assertIsNone(orden["costo_estimado"])

    def test_mismo_diagnostico_conserva_estimacion(self):
        self.preparar_estimacion()
        antes = self.detalle()

        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "teclado_touchpad",
            },
        )

        self.assertEqual(self.detalle(), antes)

    def test_estimacion_rechazada_fuera_de_diagnostico(self):
        def comprobar_rechazo():
            antes = self.detalle()

            with patch("ordenes.estimar_servicio") as estimador:
                error = self.peticion(
                    "POST",
                    f"{self.ruta}/estimacion",
                    409,
                    json={"num_repuestos": 1},
                )
                estimador.assert_not_called()

            self.assertEqual(
                error["detail"],
                "Solo se puede estimar una orden en diagnóstico.",
            )
            self.assertEqual(self.detalle(), antes)

        with self.subTest(estado="recibido"):
            comprobar_rechazo()

        self.preparar_estimacion()

        for estado in ("en_reparacion", "listo", "entregado"):
            with self.subTest(estado=estado):
                self.peticion(
                    "PATCH",
                    f"{self.ruta}/estado",
                    200,
                    json={"estado": estado},
                )
                comprobar_rechazo()

    def test_recalcular_tras_cambiar_categoria(self):
        self.preparar_estimacion()

        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "software",
            },
        )

        with patch(
            "ordenes.estimar_servicio",
            return_value={
                "tiempo_estimado_dias": 1.5,
                "costo_estimado": 150.0,
                "modelo_tiempo_sha256": "c" * 64,
                "modelo_costo_sha256": "d" * 64,
            },
        ) as estimador:
            self.peticion(
                "POST",
                f"{self.ruta}/estimacion",
                200,
                json={"num_repuestos": 0},
            )

            estimador.assert_called_once_with(
                tipo_equipo="laptop",
                marca="Lenovo",
                categoria_falla="software",
                tecnico="Técnico de prueba",
                anios_experiencia=5,
                num_repuestos=0,
                prioridad="media",
            )

        orden = self.detalle()["orden"]
        self.assertEqual(orden["estado"], "diagnostico")
        self.assertEqual(orden["tiempo_estimado_dias"], 1.5)
        self.assertEqual(orden["costo_estimado"], 150.0)
    def test_sugerencias_no_modifican_diagnostico(self):
        self.preparar_estimacion()
        antes = self.detalle()

        sugerencias = [
            {"categoria": "bateria", "puntuacion": 0.6},
            {"categoria": "teclado_touchpad", "puntuacion": 0.3},
        ]

        with patch(
            "ordenes.sugerir_fallas",
            return_value=sugerencias,
        ) as clasificador:
            respuesta = self.peticion(
                "GET",
                f"{self.ruta}/sugerencias?cantidad=2",
                200,
            )

            clasificador.assert_called_once_with(
                texto=self.orden["descripcion_falla"],
                cantidad=2,
            )

        self.assertEqual(
            respuesta,
            {
                "orden_id": self.orden["id"],
                "sugerencias": sugerencias,
            },
        )

        # Aunque la IA sugiera batería primero, el diagnóstico
        # confirmado y las estimaciones deben conservarse.
        self.assertEqual(self.detalle(), antes)

    def test_clasificacion_directa(self):
        sugerencias = [
            {"categoria": "teclado_touchpad", "puntuacion": 0.8},
        ]

        with patch(
            "main.sugerir_fallas",
            return_value=sugerencias,
        ) as clasificador:
            respuesta = self.peticion(
                "POST",
                "/ia/clasificar",
                200,
                json={
                    "descripcion": "  Varias teclas no responden.  ",
                    "cantidad": 1,
                },
            )

            clasificador.assert_called_once_with(
                texto="Varias teclas no responden.",
                cantidad=1,
            )

        self.assertEqual(respuesta, sugerencias)

    def test_clasificacion_rechaza_datos_invalidos(self):
        casos = [
            ({"descripcion": "   ", "cantidad": 3}, "descripcion"),
            ({"descripcion": "No enciende.", "cantidad": 0}, "cantidad"),
            ({"descripcion": "No enciende.", "cantidad": 12}, "cantidad"),
            ({"descripcion": "No enciende.", "cantidad": 1.5}, "cantidad"),
            ({"descripcion": "No enciende.", "cantidad": "3"}, "cantidad"),
        ]

        for datos, campo in casos:
            with self.subTest(datos=datos):
                with patch("main.sugerir_fallas") as clasificador:
                    error = self.peticion(
                        "POST",
                        "/ia/clasificar",
                        422,
                        json=datos,
                    )
                    clasificador.assert_not_called()

                self.assertTrue(any(
                    item["loc"] == ["body", campo]
                    for item in error["detail"]
                ))

    def test_comparacion_con_valores_pendientes(self):
        respuesta = self.peticion(
            "GET",
            f"{self.ruta}/comparacion",
            200,
        )

        pendiente = {
            "estimado": None,
            "real": None,
            "diferencia": None,
        }

        self.assertEqual(respuesta["tiempo_dias"], pendiente)
        self.assertEqual(respuesta["costo_soles"], pendiente)

        self.preparar_estimacion()

        respuesta = self.peticion(
            "GET",
            f"{self.ruta}/comparacion",
            200,
        )

        self.assertEqual(
            respuesta["tiempo_dias"],
            {"estimado": 2.5, "real": None, "diferencia": None},
        )
        self.assertEqual(
            respuesta["costo_soles"],
            {"estimado": 200.0, "real": None, "diferencia": None},
        )

    def test_comparacion_con_valores_reales(self):
        self.preparar_estimacion()

        ingreso = datetime.fromisoformat(self.orden["fecha_ingreso"])
        entrega = ingreso + timedelta(days=3)

        with patch("ordenes.datetime") as reloj:
            reloj.now.return_value = entrega
            self.preparar_entrega()

        antes = self.detalle()

        respuesta = self.peticion(
            "GET",
            f"{self.ruta}/comparacion",
            200,
        )

        self.assertEqual(respuesta["orden_id"], self.orden["id"])
        self.assertEqual(respuesta["estado"], "entregado")
        self.assertEqual(
            respuesta["tiempo_dias"],
            {"estimado": 2.5, "real": 3.0, "diferencia": 0.5},
        )
        self.assertEqual(
            respuesta["costo_soles"],
            {"estimado": 200.0, "real": 130.0, "diferencia": -70.0},
        )

        # Consultar la comparación no debe modificar la orden.
        self.assertEqual(self.detalle(), antes)

        # Cero es un importe válido, distinto de un valor pendiente.
        self.peticion(
            "PATCH",
            f"{self.ruta}/costo-real",
            200,
            json={"costo_real": 0},
        )

        respuesta = self.peticion(
            "GET",
            f"{self.ruta}/comparacion",
            200,
        )

        self.assertEqual(
            respuesta["costo_soles"],
            {"estimado": 200.0, "real": 0.0, "diferencia": -200.0},
        )
    def test_historial_conserva_estimaciones_anteriores(self):
        self.preparar_estimacion()

        primero = self.peticion(
            "GET", f"{self.ruta}/estimaciones", 200
        )

        self.assertEqual(len(primero), 1)
        self.assertEqual(primero[0]["orden_id"], self.orden["id"])
        self.assertEqual(primero[0]["tecnico_id"], self.tecnico_id)
        self.assertEqual(
            primero[0]["datos_entrada"],
            {
                "tipo_equipo": "laptop",
                "marca": "Lenovo",
                "categoria_falla": "teclado_touchpad",
                "tecnico": "Técnico de prueba",
                "anios_experiencia": 5,
                "num_repuestos": 1,
                "prioridad": "media",
            },
        )
        self.assertEqual(primero[0]["tiempo_estimado_dias"], 2.5)
        self.assertEqual(primero[0]["costo_estimado"], 200.0)
        self.assertEqual(primero[0]["modelo_tiempo_sha256"], "a" * 64)
        self.assertEqual(primero[0]["modelo_costo_sha256"], "b" * 64)

        self.peticion(
            "PATCH",
            f"{self.ruta}/diagnostico",
            200,
            json={
                "tecnico_id": self.tecnico_id,
                "categoria_falla": "software",
            },
        )

        # La estimación vigente se invalida, pero el historial se conserva.
        self.assertIsNone(self.detalle()["orden"]["costo_estimado"])
        self.assertIsNone(self.detalle()["orden"]["tiempo_estimado_dias"])
        self.assertEqual(
            self.peticion("GET", f"{self.ruta}/estimaciones", 200),
            primero,
        )

        with patch(
            "ordenes.estimar_servicio",
            return_value={
                "tiempo_estimado_dias": 1.5,
                "costo_estimado": 150.0,
                "modelo_tiempo_sha256": "c" * 64,
                "modelo_costo_sha256": "d" * 64,
            },
        ):
            self.peticion(
                "POST",
                f"{self.ruta}/estimacion",
                200,
                json={"num_repuestos": 0},
            )

        historial = self.peticion(
            "GET", f"{self.ruta}/estimaciones", 200
        )

        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0], primero[0])
        self.assertNotEqual(historial[0]["id"], historial[1]["id"])

        segundo = historial[1]
        self.assertEqual(segundo["datos_entrada"]["categoria_falla"], "software")
        self.assertEqual(segundo["datos_entrada"]["num_repuestos"], 0)
        self.assertEqual(segundo["modelo_tiempo_sha256"], "c" * 64)
        self.assertEqual(segundo["modelo_costo_sha256"], "d" * 64)
        self.assertEqual(segundo["tiempo_estimado_dias"], 1.5)
        self.assertEqual(segundo["costo_estimado"], 150.0)

        vigente = self.detalle()["orden"]
        self.assertEqual(vigente["tiempo_estimado_dias"], 1.5)
        self.assertEqual(vigente["costo_estimado"], 150.0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
