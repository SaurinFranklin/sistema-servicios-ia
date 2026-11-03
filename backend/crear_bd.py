from database import Base, engine
import models  # importar models registra las tablas en Base


def main():
    Base.metadata.create_all(engine)
    print("Tablas creadas:")
    for nombre in Base.metadata.tables:
        print(f"  - {nombre}")


if __name__ == "__main__":
    main()
