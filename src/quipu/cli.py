import argparse
import asyncio
import json
import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quipu.cli")


def discover_installed_plugins() -> Dict[str, Dict[str, Any]]:
    """Descubre todos los plugins externos instalados vía PyPI registrados

    bajo el grupo de Entry Points 'quipu.plugins'.
    """
    discovered_eps = entry_points(group="quipu.plugins")
    plugins: Dict[str, Dict[str, Any]] = {}

    for ep in discovered_eps:
        key = ep.name.lower().strip()

        # Extraer nombre del paquete y versión asignados por setuptools/pip
        pkg_name = (
            ep.dist.name
            if (hasattr(ep, "dist") and ep.dist is not None)
            else "Desconocido"
        )
        pkg_version = (
            ep.dist.version
            if (hasattr(ep, "dist") and ep.dist is not None)
            else "1.0.0"
        )

        plugins[key] = {
            "entry_point": ep,
            "source_key": ep.name,
            "package_name": pkg_name,
            "version": pkg_version,
            "value": ep.value,
        }

    return plugins


def list_plugins_cmd() -> None:
    """Muestra la cantidad total de plugins PyPI instalados y sus versiones."""
    plugins = discover_installed_plugins()
    total = len(plugins)

    print("\n" + "=" * 65)
    print(
        f" 📦 QUIPU CLI - PLUGINS INSTALADOS (Entry Points: 'quipu.plugins'): [{total}]"
    )
    print("=" * 65)

    if total == 0:
        print(" ⚠️  No se encontró ningún plugin instalado en el entorno.")
        print(
            "    Asegúrate de instalarlos mediante 'pip install quipu-plugin-<nombre>'."
        )
        print("=" * 65 + "\n")
        return

    for key, info in plugins.items():
        print(f" • Source Key : {info['source_key']}")
        print(f"   Paquete    : {info['package_name']}")
        print(f"   Versión    : v{info['version']}")
        print(f"   Target     : {info['value']}")
        print("-" * 65)
    print()


async def run_plugin_cmd(
    plugin_name: str, expediente_id: str, data_path: str | None = None
) -> None:
    """Instancia y ejecuta el plugin solicitado pasando el id_expediente y datos opcionales."""
    plugins = discover_installed_plugins()
    clean_key = plugin_name.lower().strip()

    if clean_key not in plugins:
        print(
            f"\n❌ Error: El plugin '{plugin_name}' no está instalado en el sistema."
        )
        available = (
            ", ".join([p["source_key"] for p in plugins.values()])
            if plugins
            else "Ninguno"
        )
        print(f"Plugins registrados: {available}\n")
        sys.exit(1)

    plugin_info = plugins[clean_key]
    ep = plugin_info["entry_point"]

    # Cargar raw_data opcional desde archivo JSON
    raw_data: Dict[str, Any] = {}
    if data_path:
        file_path = Path(data_path)
        if not file_path.exists():
            print(
                f"\n❌ Error: El archivo de entrada '{data_path}' no existe.\n"
            )
            sys.exit(1)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"\n❌ Error al parsear el archivo JSON '{data_path}': {e}\n")
            sys.exit(1)

    print(
        f"\n🚀 Cargando '{plugin_info['source_key']}' (Paquete: {plugin_info['package_name']} v{plugin_info['version']})..."
    )

    try:
        # Cargar la clase desde el Entry Point exactamente igual que en ExtractionWorkflow
        plugin_class = ep.load()
        instance = plugin_class(raw_data=raw_data)

        print(f"⚡ Ejecutando plugin para expediente ID: '{expediente_id}'...")
        result = await instance.execute(id_expediente=expediente_id)

        print("\n✅ ¡Ejecución exitosa!")
        print("=" * 65)

        # Imprimir resultado formateado
        if hasattr(result, "model_dump_json"):
            print(result.model_dump_json(by_alias=True, indent=2))
        elif hasattr(result, "model_dump"):
            print(json.dumps(result.model_dump(by_alias=True), indent=2))
        else:
            print(result)

        print("=" * 65 + "\n")

    except Exception as e:
        logger.exception("Fallo durante la ejecución del plugin '%s'", plugin_name)
        print(f"\n❌ Fallo crítico al ejecutar el plugin '{plugin_name}': {e}\n")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="quipu",
        description="Línea de comandos oficial para la gestión de plugins de Quipu.",
    )

    subparsers = parser.add_subparsers(
        dest="command", help="Comandos disponibles"
    )

    # Subcomando list
    subparsers.add_parser(
        "list",
        help="Muestra el número de plugins instalados vía PyPI y sus versiones.",
    )

    # Subcomando run
    parser_run = subparsers.add_parser(
        "run", help="Ejecuta un plugin instalado pasándole un expediente."
    )
    parser_run.add_argument(
        "plugin",
        type=str,
        help="source_key del plugin a ejecutar (ej: remaju, macho)",
    )
    parser_run.add_argument(
        "--id",
        "-i",
        required=True,
        type=str,
        help="ID del expediente judicial a procesar",
    )
    parser_run.add_argument(
        "--data",
        "-d",
        type=str,
        default=None,
        help="Ruta a un archivo JSON opcional con el payload de entrada (raw_data)",
    )

    args = parser.parse_args()

    if args.command == "list":
        list_plugins_cmd()
    elif args.command == "run":
        asyncio.run(run_plugin_cmd(args.plugin, args.id, args.data))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()