from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os
import uuid
import logging
from typing import Dict, Any, Tuple

# Configurar o logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Helper
def _split_city(city_field: str) -> Tuple[str, str]:
    """Divide uma string 'Cidade/UF' em (cidade, uf). Se não houver barra, devolve (cidade, "")."""
    if "/" in city_field:
        return tuple(city_field.split("/", 1))
    return city_field, ""


class NFSeService:
    """Serviço responsável por emitir NFSe através de web‑scraping headless."""

    def __init__(self) -> None:
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

    async def emitir_nfse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Emitir NFSe e devolver paths de PDF / XML e número gerado.

        Espera ``data`` com as seguintes chaves:
        cnpj_emissor, senha_emissor, data_emissao (dd/mm/AAAA), cnpj_cliente,
        telefone_cliente, email_cliente, valor (float) , cnae_code,
        cnae_service, city (ex. "São Paulo/SP"), descricao_servico.
        """
        # ⇒ valores derivados/formatados ------------------------------------
        valor_fmt = f"{float(data['valor']):.2f}"
        cidade, _ = _split_city(data["city"])

        resultado: Dict[str, Any] = {
            "success": False,
            "message": "Falha desconhecida",
        }

        async with async_playwright() as pw:
            browser: Browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )
            context: BrowserContext = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/118.0 Safari/537.36"
                ),
                accept_downloads=True,
            )
            page: Page = await context.new_page()

            try:
                # -----------------------------------------------------------------
                logger.info("Abrindo painel de login do emissor NFSe")
                await page.goto("https://www.nfse.gov.br/EmissorNacional/Login")

                # LOGIN -----------------------------------------------------------
                await page.fill("input[placeholder='CPF/CNPJ']", data["cnpj_emissor"])
                await page.fill("input[placeholder='Senha']", data["senha_emissor"])

                try:
                    async with page.expect_navigation(wait_until="networkidle", timeout=10000):
                        await page.click("button[type='submit']")
                except:
                    await page.click("button:has-text('Entrar')")

                try:
                    await page.wait_for_selector("#wgtAcessoRapido a", timeout=8000)
                except:
                    alerta = await page.query_selector("div.alert-warning.alert") or await page.query_selector("div[class*='alert-warning']")
                    if alerta:
                        texto_alerta = await alerta.text_content()
                        if "Usuário e/ou senha inválidos" in texto_alerta or "Usuário informado deve ser um CPF(11 dígitos) ou CNPJ(14 dígitos)." in texto_alerta:
                            resultado["message"] = "Usuário e/ou senha inválidos"
                        else:
                            resultado["message"] = f"Erro após login: {texto_alerta.strip()}"
                        return resultado
                    else:
                        resultado["message"] = "Erro após login — sem redirecionamento e sem alerta visível"
                        return resultado

                # NOVA NFSe -------------------------------------------------------
                await page.click("#wgtAcessoRapido a")

                await page.fill("#DataCompetencia", data["data_emissao"])
                await page.keyboard.press("Tab")
                await page.wait_for_timeout(800)

                # Brasil ---------------------------------------------------------
                await page.evaluate(
                    """
                    labelText => {
                        const el = [...document.querySelectorAll('label')]
                          .find(l => l.textContent.includes(labelText));
                        el?.querySelector('input')?.click();
                    }
                    """,
                    "Brasil",
                )

                # Tomador ---------------------------------------------------------
                await page.fill("#Tomador_Inscricao", data["cnpj_cliente"])
                await page.click("button:has-text('Buscar')")
                await page.fill("#Tomador_Telefone", data["telefone_cliente"])
                await page.press("#Tomador_Telefone", "Tab")
                await page.fill("#Tomador_Email", data["email_cliente"])
                await page.click("button:has-text('Avançar')")

                # Local prestação -------------------------------------------------
                await page.click("#pnlLocalPrestacao label")
                await page.fill("#pnlLocalPrestacao input.select2-search__field", cidade)
                await page.click(f"text={data['city']}")

                # Serviço ---------------------------------------------------------
                await page.fill(".select2-search__field", str(data["cnae_code"]))
                await page.wait_for_selector(".select2-results__option", timeout=3000)
                await page.press(".select2-search__field", "Enter")

                await page.click("#pnlServicoPrestado >> text=Não", strict=True)
                await page.fill("#ServicoPrestado_Descricao", data["descricao_servico"])
                await page.click("button:has-text('Avançar')")

                await page.fill("#Valores_ValorServico", valor_fmt)

                await page.evaluate(
                    """
                    labelText => {
                        const el = [...document.querySelectorAll('label')]
                          .find(l => l.textContent.includes(labelText));
                        el?.querySelector('input')?.click();
                    }
                    """,
                    "Não informar nenhum valor estimado para os Tributos",
                )

                await page.click("button:has-text('Avançar')")
                await page.click("#btnProsseguir")

                # DOWNLOADS -------------------------------------------------------
                async with page.expect_download() as dl_info:
                    await page.click("a:has-text('Baixar XML')")
                xml_dl = await dl_info.value
                xml_path = os.path.join(self.download_dir, f"nfse_{uuid.uuid4().hex}.xml")
                await xml_dl.save_as(xml_path)

                async with page.expect_download() as dl_info:
                    await page.click("a:has-text('Baixar DANFSe')")
                pdf_dl = await dl_info.value
                pdf_path = os.path.join(self.download_dir, f"nfse_{uuid.uuid4().hex}.pdf")
                await pdf_dl.save_as(pdf_path)

                numero_nfse = f"NFSE-{uuid.uuid4().hex[:8].upper()}"
                logger.info("NFSe emitida com sucesso %s", numero_nfse)

                resultado.update(
                    {
                        "success": True,
                        "message": "NFSe emitida com sucesso",
                        "xml_path": xml_path,
                        "pdf_path": pdf_path,
                        "numero_nfse": numero_nfse,
                    }
                )
                return resultado

            except Exception as exc:
                logger.exception("Erro durante a emissão: %s", exc)
                resultado["message"] = f"Erro durante a emissão: {exc}"
                return resultado

            finally:
                await context.close()
                await browser.close()
        return resultado
    

    def upload_to_s3(self, file_path: str, file_key: str) -> str:
        """
        Faz upload de arquivo para S3 (adaptado do emissor.py original)
        """
        try:
            import boto3
            
            # Configurações AWS (devem vir de variáveis de ambiente em produção)
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', 'AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'AWS_SECRET_ACCESS')
            aws_region = os.getenv('AWS_REGION', 'AWS_REGION')
            bucket_name = os.getenv('AWS_BUCKET_NAME', 'YOUR_BUCKET_NAME')
            
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region
            )
            
            s3.upload_file(file_path, bucket_name, file_key)
            os.remove(file_path)  # Remove arquivo local após upload
            
            file_url = f'https://{bucket_name}.s3.amazonaws.com/{file_key}'
            return file_url
            
        except Exception as e:
            logger.error(f"Erro no upload para S3: {str(e)}")
            return str(e)

