import argparse
import csv
from datetime import date
from pathlib import Path

import requests

DATASETS = {
    "ingresos": {
        "dataset_id": "44kq-qq64",
        "filename_prefix": "RESUMEN_INGRESOS_PRESUPUESTO_GENERAL_DE_BUCARAMANGA",
    },
    "egresos": {
        "dataset_id": "ys3r-h9d3",
        "filename_prefix": "RESUMEN_EGRESOS_PRESUPUESTO_GENERAL_DEL_MUNICIPIO_DE_BUCARAMANGA",
    },
}


def build_csv_url(dataset_id: str) -> str:
    return f"https://www.datos.gov.co/api/views/{dataset_id}/rows.csv?accessType=DOWNLOAD"


def build_metadata_url(dataset_id: str) -> str:
    return f"https://www.datos.gov.co/api/views/{dataset_id}.json"


def download_csv(url: str, destination: Path) -> None:
    response = requests.get(
        url,
        timeout=120,
        stream=True,
        headers={"User-Agent": "hormiga-culona-pipeline/1.0"},
    )
    response.raise_for_status()
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                handle.write(chunk)


def fetch_metadata(url: str) -> dict:
    response = requests.get(url, timeout=60, headers={"User-Agent": "hormiga-culona-pipeline/1.0"})
    response.raise_for_status()
    return response.json()


def write_descriptions_csv(output_path: Path, descriptions: list[dict[str, str]]) -> Path:
    destination = output_path / "data_base_descriptions.csv"
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["data_base_name", "description"])
        writer.writeheader()
        writer.writerows(descriptions)
    return destination


def run_extract(output_dir: str = ".", run_label: str | None = None) -> dict[str, str]:
    run_label = run_label or date.today().strftime("%Y%m%d")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, str] = {}
    descriptions: list[dict[str, str]] = []
    for name, dataset in DATASETS.items():
        filename = f"{dataset['filename_prefix']}_{run_label}.csv"
        destination = output_path / filename
        download_csv(build_csv_url(dataset["dataset_id"]), destination)
        metadata = fetch_metadata(build_metadata_url(dataset["dataset_id"]))
        descriptions.append({
            "data_base_name": name,
            "description": (metadata.get("description") or "").strip(),
        })
        downloaded[name] = str(destination)
        print(f"[OK] {name}: {destination}")

    descriptions_path = write_descriptions_csv(output_path, descriptions)
    downloaded["descriptions"] = str(descriptions_path)
    print(f"[OK] descriptions: {descriptions_path}")
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga datasets de ingresos y egresos de datos.gov.co")
    parser.add_argument("--output-dir", default=".", help="Directorio destino para los CSV descargados")
    parser.add_argument("--run-label", default=None, help="Sufijo para los archivos descargados")
    args = parser.parse_args()
    run_extract(output_dir=args.output_dir, run_label=args.run_label)


if __name__ == "__main__":
    main()
