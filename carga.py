from sqlalchemy import create_engine, text, Table, Column, Integer, String, Float, MetaData
from sqlalchemy.orm import sessionmaker
import pandas as pd
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para mapear tipos de datos de Pandas a SQLAlchemy
def mapear_tipos(columna):
    if pd.api.types.is_integer_dtype(columna):
        return Integer
    elif pd.api.types.is_float_dtype(columna):
        return Float
    elif pd.api.types.is_string_dtype(columna):
        return String
    else:
        return String  # Por defecto, cualquier otro tipo se mapea como String

# Función para cargar datos de un archivo Excel a PostgreSQL
def cargar_excel_a_postgresql(file_path, sheet_name, db_url, table_name):
    try:
        # Leer el archivo Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.info(f"Hoja '{sheet_name}' del archivo Excel leída correctamente.")
        
        # Conectar a PostgreSQL
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Borrar el contenido de la tabla sin eliminar la estructura
            session.execute(text(f"DELETE FROM {table_name}"))
            session.commit()
            logger.info(f"Contenido de la tabla '{table_name}' eliminado correctamente.")

            # Cargar los datos en la tabla
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logger.info("Datos cargados exitosamente en PostgreSQL.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error durante la carga de datos: {e}")
            raise
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error: {e}")

# Parámetros
ruta_carpeta = os.path.join('..', 'bd')
file_path = os.path.join(ruta_carpeta, 'BD.xlsx')
sheet_name = 'ROTACIÓN'
db_url = os.getenv('DATABASE_URL')
table_name = 'demanda'

# Llamada a la función
cargar_excel_a_postgresql(file_path, sheet_name, db_url, table_name)
