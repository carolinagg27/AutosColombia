-- AUTOS COLOMBIA | Modelo físico SQLite
-- Fechas en formato ISO: YYYY-MM-DD y YYYY-MM-DD HH:MM:SS
-- Los cambios de movimiento/celda deben realizarse en una misma transacción.
PRAGMA foreign_keys = ON;

CREATE TABLE usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    contrasena_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('Administrador', 'Operario')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE cliente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    documento TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    telefono TEXT
);

CREATE TABLE vehiculo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    placa TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK (tipo IN ('Carro', 'Moto')),
    cliente_id INTEGER NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES cliente(id)
);

CREATE TABLE celda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL CHECK (tipo IN ('Carro', 'Moto')),
    estado TEXT NOT NULL DEFAULT 'Disponible'
        CHECK (estado IN ('Disponible', 'Ocupada', 'Fuera de servicio'))
);

CREATE TABLE mensualidad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    valor_cop INTEGER NOT NULL CHECK (valor_cop > 0),
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculo(id),
    CHECK (fecha_fin >= fecha_inicio)
);

-- Versión académica: cada mensualidad se paga en una sola transacción.
CREATE TABLE pago (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensualidad_id INTEGER NOT NULL UNIQUE,
    usuario_id INTEGER NOT NULL,
    fecha_pago TEXT NOT NULL,
    valor_cop INTEGER NOT NULL CHECK (valor_cop > 0),
    metodo TEXT NOT NULL CHECK (metodo IN ('Efectivo', 'Transferencia')),
    FOREIGN KEY (mensualidad_id) REFERENCES mensualidad(id),
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);

CREATE TABLE movimiento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id INTEGER NOT NULL,
    celda_id INTEGER NOT NULL,
    usuario_entrada_id INTEGER NOT NULL,
    usuario_salida_id INTEGER,
    fecha_entrada TEXT NOT NULL,
    fecha_salida TEXT,
    estado TEXT NOT NULL DEFAULT 'Activo'
        CHECK (estado IN ('Activo', 'Cerrado')),
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculo(id),
    FOREIGN KEY (celda_id) REFERENCES celda(id),
    FOREIGN KEY (usuario_entrada_id) REFERENCES usuario(id),
    FOREIGN KEY (usuario_salida_id) REFERENCES usuario(id),
    CHECK (
       (estado = 'Activo' AND fecha_salida IS NULL AND usuario_salida_id IS NULL)
       OR
       (estado = 'Cerrado' AND fecha_salida IS NOT NULL
        AND usuario_salida_id IS NOT NULL AND fecha_salida >= fecha_entrada)
    )
);

-- Un vehículo y una celda no pueden tener dos movimientos activos.
CREATE UNIQUE INDEX idx_vehiculo_activo
ON movimiento(vehiculo_id) WHERE estado = 'Activo';

CREATE UNIQUE INDEX idx_celda_ocupada
ON movimiento(celda_id) WHERE estado = 'Activo';

CREATE TABLE novedad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movimiento_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    descripcion TEXT NOT NULL CHECK (length(trim(descripcion)) > 0),
    fecha TEXT NOT NULL,
    FOREIGN KEY (movimiento_id) REFERENCES movimiento(id),
    FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);

-- Reglas implementadas en Python/Flask:
-- 1. Validar placa, celda compatible y mensualidad vigente con pago.
-- 2. Verificar que el pago corresponda al valor total de la mensualidad.
-- 3. Actualizar movimiento y estado de celda de forma atómica.
-- 4. Al registrar salida, permitirla incluso si la mensualidad venció.
