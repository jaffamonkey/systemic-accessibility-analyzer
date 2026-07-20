from adapters import load_adapters
from services.report_loader import load_reports
from services.processing_engine import process_rows
from services.cluster_engine import build_clusters
from services.metrics_engine import calculate_metrics


def main():
    load_adapters()
    raw = load_reports('reports')
    rows = process_rows(raw)
    clusters = build_clusters(rows)
    metrics = calculate_metrics(rows, clusters)

    print({
        'raw': len(raw),
        'rows': len(rows),
        'clusters': len(clusters),
        'pages': metrics['pages'],
        'sources': metrics['source_counts'],
    })


if __name__ == '__main__':
    main()
