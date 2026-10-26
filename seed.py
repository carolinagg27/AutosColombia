"""Crea usuarios de prueba y espacios de ejemplo. Ejecutar una sola vez."""
import os
import secrets
from datetime import timedelta

from werkzeug.security import generate_password_hash

from app import ahora_colombia, create_app
from app.models import db, Usuario, Cliente, Vehiculo, Celda, Mensualidad, Pago


def preparar_datos():
    app = create_app()
    with app.app_context():
        if Usuario.query.count() > 0:
            print("La base ya tiene usuarios. No se han creado cuentas duplicadas.")
            return
        admin_password = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        operario_password = os.getenv("OPERARIO_PASSWORD") or secrets.token_urlsafe(12)
        if len(admin_password) < 8 or len(operario_password) < 8:
            raise ValueError("Las contraseñas deben tener al menos 8 caracteres.")
        admin = Usuario(nombre="Administrador General", usuario="admin",
                        contrasena_hash=generate_password_hash(admin_password), rol="Administrador", activo=True)
        operario = Usuario(nombre="Operario de Prueba", usuario="operario",
                          contrasena_hash=generate_password_hash(operario_password), rol="Operario", activo=True)
        db.session.add_all([admin, operario])
        db.session.flush()
        for i in range(1, 9):
            db.session.add(Celda(numero=f"C-{i:02d}", tipo="Carro", estado="Disponible"))
        for i in range(1, 5):
            db.session.add(Celda(numero=f"M-{i:02d}", tipo="Moto", estado="Disponible"))
        cliente = Cliente(documento="1000000001", nombre="Cliente de ejemplo", telefono="3000000000")
        db.session.add(cliente)
        db.session.flush()
        vehiculo = Vehiculo(placa="ABC123", tipo="Carro", cliente_id=cliente.id)
        db.session.add(vehiculo)
        db.session.flush()
        hoy = ahora_colombia().date()
        mensualidad = Mensualidad(vehiculo_id=vehiculo.id, fecha_inicio=hoy,
                                  fecha_fin=hoy + timedelta(days=29), valor_cop=160000)
        db.session.add(mensualidad)
        db.session.flush()
        db.session.add(Pago(mensualidad_id=mensualidad.id, usuario_id=admin.id,
                           fecha_pago=ahora_colombia(), valor_cop=160000, metodo="Efectivo"))
        db.session.commit()
        print("¡Datos de prueba creados correctamente!")
        print(f"Administrador: admin / {admin_password}")
        print(f"Operario:      operario / {operario_password}")
        print("Guarda estas contraseñas. No se volverán a mostrar al ejecutar seed.py.")
        print("Vehículo de ejemplo: ABC123 (mensualidad vigente y pagada)")


if __name__ == "__main__":
    preparar_datos()
