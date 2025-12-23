"""Security Log Analytics Pipeline - ETL Script

Este script extrae logs de seguridad desde Supabase, los transforma usando Polars
y genera un reporte HTML que se envía por email.
"""

import os
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import polars as pl

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SecurityAnalyticsPipeline:
    """Pipeline ETL para análisis de logs de seguridad."""

    def __init__(self, use_mock: bool = False):
        """Inicializa el pipeline con configuración opcional de mock data.

        Args:
            use_mock: Si True, usa datos mock en lugar de Supabase.
        """
        self.use_mock = use_mock

        if not use_mock:
            self._load_credentials()
            self._init_clients()

    def _load_credentials(self) -> None:
        """Carga credenciales desde variables de entorno."""
        from dotenv import load_dotenv
        load_dotenv()

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.resend_key = os.getenv("RESEND_API_KEY")
        self.admin_email = os.getenv("ADMIN_EMAIL")

        if not all([self.supabase_url, self.supabase_key, self.resend_key]):
            raise ValueError("❌ Missing required environment variables.")

    def _init_clients(self) -> None:
        """Inicializa clientes de Supabase y Resend."""
        from supabase import create_client
        import resend

        self.supabase = create_client(self.supabase_url, self.supabase_key)
        resend.api_key = self.resend_key

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """Calcula el rango de fechas del mes anterior.

        Returns:
            Tupla con (fecha_inicio, fecha_fin) del mes anterior.
        """
        today = datetime.now()
        first_day_current = today.replace(day=1)
        last_day_prev = first_day_current - timedelta(days=1)
        first_day_prev = last_day_prev.replace(day=1)

        return first_day_prev, first_day_current

    def extract(self) -> pl.DataFrame:
        """Paso EXTRACT: Obtiene logs desde Supabase o datos mock.

        Returns:
            DataFrame con logs crudos.
        """
        if self.use_mock:
            return self._extract_mock_data()

        start_date, end_date = self.get_date_range()
        logging.info(f"📡 Extracting logs from {start_date.date()} to {end_date.date()}...")

        try:
            response = self.supabase.table("access_logs") \
                .select("*") \
                .gte("timestamp", start_date.isoformat()) \
                .lt("timestamp", end_date.isoformat()) \
                .execute()

            data = response.data
            if not data:
                logging.warning("⚠️ No logs found for this period.")
                return pl.DataFrame()

            logging.info(f"✅ Successfully extracted {len(data)} records.")
            return pl.DataFrame(data)

        except Exception as e:
            logging.error(f"❌ Extraction failed: {e}")
            raise

    def _extract_mock_data(self) -> pl.DataFrame:
        """Carga datos mock desde CSV.

        Returns:
            DataFrame con datos de ejemplo.
        """
        logging.info("📡 Loading mock data...")
        try:
            df = pl.read_csv("data/mock_logs.csv")
            logging.info(f"✅ Loaded {len(df)} mock records.")
            return df
        except FileNotFoundError:
            logging.error("❌ Mock data file not found.")
            return pl.DataFrame()

    def transform(self, df: pl.DataFrame) -> Dict:
        """Paso TRANSFORM: Limpia datos y calcula métricas de negocio.

        Args:
            df: DataFrame con logs crudos.

        Returns:
            Diccionario con métricas calculadas.
        """
        if df.is_empty():
            return {}

        logging.info("⚙️ Transforming data and calculating metrics...")

        # 1. Conversión de tipos
        df = df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime))

        # 2. Segmentación
        attacks_df = df.filter(pl.col('action').is_in(['geo_blocked', 'path_blocked', 'bot_blocked']))
        legitimate_df = df.filter(pl.col('action') == 'legitimate')

        # 3. Agregaciones
        top_countries = attacks_df.group_by('country').len().sort('len', descending=True).head(5)
        top_countries_dict = dict(zip(top_countries['country'], top_countries['len']))

        # IPs sospechosas (más de 5 bloqueos)
        suspicious_ips = attacks_df.group_by('ip').len().filter(pl.col('len') > 5).sort('len', descending=True).head(8)
        suspicious_ips_dict = dict(zip(suspicious_ips['ip'], suspicious_ips['len']))

        # Rendimiento
        avg_latency = df.select(pl.col('response_time_ms').mean()).item()

        start_date, _ = self.get_date_range()

        return {
            "report_date": start_date.strftime("%B %Y"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_requests": len(df),
                "blocked_requests": len(attacks_df),
                "security_score": round((len(attacks_df) / len(df)) * 100, 2) if len(df) > 0 else 0,
                "avg_latency_ms": int(avg_latency) if avg_latency is not None else 0
            },
            "geo_analysis": top_countries_dict,
            "threat_intel": suspicious_ips_dict,
            "traffic_quality": {
                "legitimate": len(legitimate_df),
                "bots": len(df.filter(pl.col('action') == 'bot_allowed'))
            }
        }

    def load(self, metrics: Dict) -> None:
        """Paso LOAD: Genera reporte HTML y lo envía por email.

        Args:
            metrics: Diccionario con métricas calculadas.
        """
        if not metrics:
            logging.warning("⚠️ No metrics to report.")
            return

        logging.info("✉️ Generating report and sending email...")

        html_content = self._generate_html_report(metrics)

        if self.use_mock:
            logging.info("📧 Mock mode - report generated but not sent.")
            self._save_report_locally(html_content)
            return

        try:
            import resend
            resend.Emails.send({
                "from": "Security Bot <onboarding@resend.dev>",
                "to": [self.admin_email],
                "subject": f"Security Report - {metrics['report_date']}",
                "html": html_content
            })
            logging.info("✅ Report dispatched successfully.")
        except Exception as e:
            logging.error(f"❌ Failed to send email: {e}")

    def _generate_html_report(self, metrics: Dict) -> str:
        """Genera HTML del reporte.

        Args:
            metrics: Métricas calculadas.

        Returns:
            String HTML renderizado.
        """
        geo_rows = ''.join([
            f'<tr><td style="padding: 8px; border-bottom: 1px solid #eee;">{k}</td>'
            f'<td style="padding: 8px; border-bottom: 1px solid #eee;">{v}</td></tr>'
            for k, v in metrics['geo_analysis'].items()
        ])

        threat_items = ''.join([
            f'<li><code>{ip}</code>: {count} blocks</li>'
            for ip, count in metrics['threat_intel'].items()
        ])

        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px;">
                <div style="background: #2563eb; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin:0;">🛡️ Monthly Security Intelligence</h2>
                    <p style="margin:5px 0 0 0;">Period: {metrics['report_date']}</p>
                </div>

                <div style="padding: 20px;">
                    <h3>📊 Executive Summary</h3>
                    <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                        <div style="background: #f8fafc; padding: 10px; flex: 1; border-radius: 4px;">
                            <strong>Total Traffic</strong><br>{metrics['summary']['total_requests']:,}
                        </div>
                        <div style="background: #fee2e2; padding: 10px; flex: 1; border-radius: 4px;">
                            <strong>Threats Blocked</strong><br>{metrics['summary']['blocked_requests']:,}
                        </div>
                        <div style="background: #f0fdf4; padding: 10px; flex: 1; border-radius: 4px;">
                            <strong>Avg Latency</strong><br>{metrics['summary']['avg_latency_ms']}ms
                        </div>
                    </div>

                    <h3>🌍 Top Attack Origins</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f1f5f9; text-align: left;">
                            <th style="padding: 8px;">Country</th>
                            <th style="padding: 8px;">Blocked Attempts</th>
                        </tr>
                        {geo_rows}
                    </table>

                    <h3>⚠️ High Risk IPs (Watchlist)</h3>
                    <ul>{threat_items}</ul>
                </div>

                <div style="background: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px;">
                    Generated automatically by Data Engineering Pipeline • {metrics['generated_at']}
                </div>
            </div>
        </body>
        </html>
        """

    def _save_report_locally(self, html_content: str) -> None:
        """Guarda reporte localmente en modo mock.

        Args:
            html_content: Contenido HTML del reporte.
        """
        output_path = "examples/generated_report.html"
        os.makedirs("examples", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html_content)
        logging.info(f"📄 Report saved to {output_path}")

    def run(self) -> None:
        """Ejecuta el pipeline completo ETL."""
        logging.info("🚀 Starting Security Analytics Pipeline...")
        df = self.extract()
        metrics = self.transform(df)
        self.load(metrics)
        logging.info("✅ Pipeline completed successfully.")

def main():
    parser = argparse.ArgumentParser(description='Security Log Analytics Pipeline')
    parser.add_argument('--use-mock-data', action='store_true',
                       help='Use mock data instead of Supabase')
    args = parser.parse_args()

    pipeline = SecurityAnalyticsPipeline(use_mock=args.use_mock_data)
    pipeline.run()

if __name__ == "__main__":
    main()
