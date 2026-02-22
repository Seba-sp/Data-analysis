"""
CL-only CLI entrypoint with interactive menu.
"""

from __future__ import annotations

import sys
from datetime import datetime

from cl_data_processor import (
    list_cl_input_sets,
    process_all_sets,
    process_cl_set,
    process_from_list,
)
from cl_master import (
    build_cl_master_full_reset,
    build_cl_master_incremental,
)
from config import INPUT_DIR, ensure_directories


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_processing_report(results: list, mode: str) -> None:
    """Save a txt report of failed sets so the user knows what to fix."""
    failed = [r for r in results if not r["success"]]
    if not failed:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = INPUT_DIR / f"resultados_procesar_{timestamp}.txt"

    lines = [
        "=" * 60,
        f"REPORTE DE PROCESAMIENTO",
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Modo: {mode}",
        "=" * 60,
        f"Total: {len(results)}",
        f"Exitosos: {len(results) - len(failed)}",
        f"Fallidos: {len(failed)}",
        "=" * 60,
        "",
        "SETS FALLIDOS:",
        "-" * 60,
    ]

    for r in failed:
        lines.append(f"{r['code']}:")
        for issue in r["issues"]:
            lines.append(f"  - {issue}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReporte guardado en: {report_path}")


def _print_processing_results(results: list, mode: str) -> None:
    """Print a summary table of processing results and save report if failures."""
    succeeded = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\n{'='*60}")
    print(f"RESUMEN DE PROCESAMIENTO")
    print(f"{'='*60}")
    print(f"  Total:       {len(results)}")
    print(f"  Exitosos:    {len(succeeded)}")
    print(f"  Con errores: {len(failed)}")

    if failed:
        print(f"\n  DETALLE DE ERRORES:")
        print(f"  {'-'*56}")
        for r in failed:
            for issue in r["issues"]:
                print(f"  {r['code']}: {issue}")

    # Print warnings for successful ones that had non-critical issues
    warned = [r for r in succeeded if r["issues"]]
    if warned:
        print(f"\n  ADVERTENCIAS (procesados con warnings):")
        print(f"  {'-'*56}")
        for r in warned:
            for issue in r["issues"]:
                print(f"  {r['code']}: {issue}")

    print(f"{'='*60}")

    _save_processing_report(results, mode)


def _print_consolidation_result(df, issues, path, mode_label: str) -> None:
    """Print consolidation summary."""
    print(f"\n{'='*60}")
    print(f"CONSOLIDACION - {mode_label}")
    print(f"{'='*60}")
    print(f"  Master guardado en: {path}")
    print(f"  Filas totales:      {len(df)}")
    if not df.empty:
        print(f"  Textos unicos:      {df['Codigo Texto'].astype(str).nunique()}")

    if issues:
        print(f"\n  ADVERTENCIAS:")
        for issue in issues:
            print(f"  - {issue}")

    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Processing sub-menu
# ---------------------------------------------------------------------------

def menu_process() -> None:
    """Sub-menu for processing files."""
    while True:
        # Show available sets
        sets = list_cl_input_sets()
        print(f"\n{'='*60}")
        print(f"  PROCESAR ARCHIVOS")
        print(f"  ({len(sets)} pares docx+xlsx encontrados en input/)")
        print(f"{'='*60}")
        print(f"  [1] Procesar un set (elegir de la lista)")
        print(f"  [2] Procesar desde procesar.txt")
        print(f"  [3] Procesar todos los sets en input/")
        print(f"  [0] Volver")
        print(f"{'='*60}")

        choice = input("\nOpcion: ").strip()

        if choice == "0":
            return

        if choice == "1":
            _process_single_interactive()

        elif choice == "2":
            list_path = INPUT_DIR / "procesar.txt"
            if not list_path.exists():
                print(f"\nNo se encontro {list_path}")
                print("Crea un archivo procesar.txt en input/ con un codigo por linea (ej: C001)")
                continue

            results = process_from_list(list_path)
            _print_processing_results(results, "procesar.txt")
            input("\nPresiona Enter para continuar...")

        elif choice == "3":
            results = process_all_sets()
            _print_processing_results(results, "Todos los sets")
            input("\nPresiona Enter para continuar...")

        else:
            print("Opcion invalida.")


def _process_single_interactive() -> None:
    """Let the user pick one set from the list and process it."""
    sets = list_cl_input_sets()

    if not sets:
        print("\nNo se encontraron pares docx+xlsx en input/")
        return

    print(f"\n{'='*60}")
    print(f"  SELECCIONAR SET")
    print(f"{'='*60}")
    for idx, s in enumerate(sets, 1):
        print(f"  [{idx}] {s.codigo_texto}")
        print(f"      {s.docx_path.name}")
        print(f"      {s.excel_path.name}")
        print()
    print(f"  [0] Volver")
    print(f"{'='*60}")

    while True:
        try:
            pick = input("\nOpcion: ").strip()
            pick_num = int(pick)

            if pick_num == 0:
                return

            if 1 <= pick_num <= len(sets):
                selected = sets[pick_num - 1]
                print(f"\nProcesando {selected.codigo_texto}...")
                success, issues = process_cl_set(selected)

                if success:
                    print(f"\n[OK] {selected.codigo_texto} procesado exitosamente.")
                else:
                    print(f"\n[ERROR] {selected.codigo_texto} no se pudo procesar.")

                if issues:
                    for issue in issues:
                        print(f"  - {issue}")

                input("\nPresiona Enter para continuar...")
                return
            else:
                print(f"Numero invalido. Ingresa entre 0 y {len(sets)}")
        except ValueError:
            print("Entrada invalida. Ingresa un numero.")
        except KeyboardInterrupt:
            print("\nCancelado.")
            return


# ---------------------------------------------------------------------------
# Consolidation sub-menu
# ---------------------------------------------------------------------------

def menu_consolidate() -> None:
    """Sub-menu for master consolidation."""
    while True:
        print(f"\n{'='*60}")
        print(f"  CONSOLIDAR MASTER EXCEL")
        print(f"{'='*60}")
        print(f"  [1] Incremental (solo agregar archivos nuevos)")
        print(f"  [2] Full reset (reconstruir master completo)")
        print(f"  [0] Volver")
        print(f"{'='*60}")

        choice = input("\nOpcion: ").strip()

        if choice == "0":
            return

        if choice == "1":
            df, issues, path = build_cl_master_incremental()
            _print_consolidation_result(df, issues, path, "INCREMENTAL")
            input("\nPresiona Enter para continuar...")
            return

        if choice == "2":
            df, issues, path = build_cl_master_full_reset()
            _print_consolidation_result(df, issues, path, "FULL RESET")
            input("\nPresiona Enter para continuar...")
            return

        print("Opcion invalida.")


# ---------------------------------------------------------------------------
# Main interactive menu
# ---------------------------------------------------------------------------

def interactive_menu() -> None:
    """Main interactive menu loop."""
    while True:
        print(f"\n{'='*60}")
        print(f"  GENERADOR CL - MENU PRINCIPAL")
        print(f"{'='*60}")
        print(f"  [1] Procesar archivos (validar y copiar a processed)")
        print(f"  [2] Consolidar master Excel")
        print(f"  [3] Salir")
        print(f"{'='*60}")

        try:
            choice = input("\nOpcion: ").strip()

            if choice == "1":
                menu_process()
            elif choice == "2":
                menu_consolidate()
            elif choice == "3":
                print("Saliendo...")
                sys.exit(0)
            else:
                print("Opcion invalida. Ingresa 1, 2 o 3.")

        except KeyboardInterrupt:
            print("\nCancelado.")
            continue


def main() -> None:
    ensure_directories()

    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\nSaliendo...")
        sys.exit(0)


if __name__ == "__main__":
    main()
