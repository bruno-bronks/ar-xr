"""Modelo de custo reproduzivel (SPEC-012, REQ-OPS-008; D-049). So stdlib.

Todo preco carrega fonte, data de coleta e se foi confirmado na pagina OFICIAL do provedor. Os coletados
nesta sessao vieram de agregadores/blogs de terceiros (`official=False`) e DEVEM ser reconfirmados antes de
qualquer decisao de gasto. Moedas nao sao convertidas (nenhuma taxa de cambio foi coletada): cada cenario
usa uma moeda so. O relatorio `docs/cloud/cost-estimate.md` e gerado daqui e um teste garante que nao diverge.
"""

from dataclasses import dataclass
from datetime import date

HOURS_PER_MONTH = 730.0
RETRIEVED = date(2026, 10, 20)


@dataclass(frozen=True)
class Price:
    key: str
    unit: str  # "mes" | "hora" | "GB-mes" | "GB"
    amount: float
    currency: str
    source_url: str
    retrieved: date
    official: bool
    free: float = 0.0  # franquia mensal gratuita (na unidade do preco)
    note: str = ""


PRICES: dict[str, Price] = {
    p.key: p
    for p in (
        Price(
            "hetzner_cpx22", "mes", 19.99, "EUR",
            "https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do",
            RETRIEVED, False,
            note="2 vCPU, 4 GB, 80 GB, IPv4 incluso, sem IVA; terceiros relatam reajuste de jun/2026",
        ),
        Price(
            "aws_t4g_small", "hora", 0.0168, "USD",
            "https://calculator.holori.com/aws/ec2/t4g.small/us-east-1",
            RETRIEVED, False, note="2 vCPU Arm, 2 GB, Linux sob demanda, us-east-1",
        ),
        Price(
            "aws_ebs_gp3", "GB-mes", 0.08, "USD",
            "https://www.factualminds.com/blog/amazon-ebs-pricing-orphaned-volumes-snapshots/",
            RETRIEVED, False, note="us-east-1; IOPS/vazao base inclusas",
        ),
        Price(
            "aws_s3_standard", "GB-mes", 0.023, "USD",
            "https://upstash.com/blog/aws-s3-pricing-explained-2026",
            RETRIEVED, False, note="us-east-1; sem custo de requisicoes no modelo (volume baixo)",
        ),
        Price(
            "aws_egress", "GB", 0.09, "USD",
            "https://infratally.com/articles/aws-s3-pricing-explained-2026/",
            RETRIEVED, False, free=100.0, note="saida para a internet; 100 GB/mes gratis agregados",
        ),
    )
}  # fmt: skip


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    hosts: int
    disk_gb: float  # por host; so cobrado se `disk` tiver preco
    backup_gb: float
    egress_gb: float
    vm: str
    disk: str | None
    backup: str | None
    egress: str | None
    note: str = ""


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "hml-hetzner", "Homologação — 1 VM Hetzner CPX22", 1, 80, 5, 20,
        vm="hetzner_cpx22", disk=None, backup=None, egress=None,
        note="Disco de 80 GB incluso. Backup fica no MESMO host (sem custo, mas não protege contra perda do host); "
        "preço de armazenamento externo da Hetzner não foi coletado.",
    ),
    Scenario(
        "hml-aws", "Homologação — 1 VM AWS t4g.small", 1, 30, 5, 20,
        vm="aws_t4g_small", disk="aws_ebs_gp3", backup="aws_s3_standard", egress="aws_egress",
        note="2 GB de RAM é o mínimo: os limites do Compose somam ≈ 1,4 GB (sem Prometheus).",
    ),
    Scenario(
        "prod-aws", "Produção pequena — 2 VMs AWS t4g.small (principal + reserva)", 2, 50, 50, 100,
        vm="aws_t4g_small", disk="aws_ebs_gp3", backup="aws_s3_standard", egress="aws_egress",
        note="Sem balanceador, sem banco gerenciado e sem WAF (não precificados). A reserva exige replicação do banco, "
        "que NÃO está implementada.",
    ),
)  # fmt: skip


@dataclass(frozen=True)
class Cost:
    currency: str
    items: dict[str, float]

    @property
    def total(self) -> float:
        return sum(self.items.values())


def _billable(price: Price, quantity: float) -> float:
    return max(quantity - price.free, 0.0) * price.amount


def monthly_cost(scenario: Scenario, prices: dict[str, Price]) -> Cost:
    used = [prices[k] for k in (scenario.vm, scenario.disk, scenario.backup, scenario.egress) if k]
    currencies = {p.currency for p in used}
    if len(currencies) != 1:
        raise ValueError(f"a scenario must use a single currency, got {sorted(currencies)}")
    vm = prices[scenario.vm]
    per_vm = vm.amount * (HOURS_PER_MONTH if vm.unit == "hora" else 1.0)
    items = {"compute": per_vm * scenario.hosts}
    if scenario.disk:
        items["disk"] = _billable(prices[scenario.disk], scenario.disk_gb * scenario.hosts)
    if scenario.backup:
        items["backup"] = _billable(prices[scenario.backup], scenario.backup_gb)
    if scenario.egress:
        items["egress"] = _billable(prices[scenario.egress], scenario.egress_gb)
    return Cost(currencies.pop(), items)


def storage_growth_gb_per_month(
    *, devices: int, sensors: int, interval_s: float, bytes_per_row: float
) -> float:
    rows = devices * sensors * (86_400 / interval_s) * 30
    return rows * bytes_per_row / 1e9


BYTES_PER_ROW = 340.0  # MEDIDO na homologacao: pg_total_relation_size/linhas = 339 B (2.080 linhas)


def render_markdown() -> str:
    lines = [
        "# Estimativa de custos (Fase 6)",
        "",
        "> **Nenhum serviço pago foi contratado e nenhum recurso de nuvem foi criado.** Isto é uma **estimativa** "
        "reproduzível (`python scripts/cost_model.py --write`), não um orçamento. Os preços abaixo foram coletados "
        f"em {RETRIEVED.isoformat()} de **fontes de terceiros** (agregadores e blogs) — **nenhum foi confirmado na "
        "página oficial** do provedor — e precisam ser reconfirmados antes de qualquer decisão de gasto. "
        "Impostos (IVA etc.) não estão incluídos. Moedas não são convertidas (nenhuma taxa de câmbio foi coletada).",
        "",
        "## Preços de lista usados",
        "",
        "| Item | Unidade | Valor | Moeda | Franquia | Oficial? | Coletado | Fonte | Nota |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in PRICES.values():
        free = f"{p.free:g}" if p.free else "—"
        official = "sim" if p.official else "**não (terceiros)**"
        lines.append(
            f"| {p.key} | {p.unit} | {p.amount:g} | {p.currency} | {free} | {official} | "
            f"{p.retrieved.isoformat()} | [fonte]({p.source_url}) | {p.note} |"
        )
    lines += [
        "",
        f"Horas por mês consideradas: {HOURS_PER_MONTH:g} (preços por hora multiplicados por {HOURS_PER_MONTH:g}).",
        "",
        "## Cenários (custo mensal)",
        "",
        "| Cenário | Moeda | Computação | Disco | Backup | Saída (egress) | **Total/mês** |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in SCENARIOS:
        cost = monthly_cost(s, PRICES)
        cells = [
            f"{cost.items[k]:.2f}" if k in cost.items else "—"
            for k in ("compute", "disk", "backup", "egress")
        ]
        lines.append(
            f"| {s.title} | {cost.currency} | " + " | ".join(cells) + f" | **{cost.total:.2f}** |"
        )
    lines += ["", "Premissas por cenário:", ""]
    for s in SCENARIOS:
        lines.append(
            f"- **{s.title}** — {s.hosts} host(s); disco {s.disk_gb:g} GB/host; backup retido {s.backup_gb:g} GB; "
            f"saída {s.egress_gb:g} GB/mês. {s.note}"
        )
    lines += [
        "",
        "## Crescimento do armazenamento de telemetria",
        "",
        f"Premissa **medida em pequena escala**: {BYTES_PER_ROW:g} bytes por linha de `telemetry_events` "
        "(`pg_total_relation_size` ÷ linhas = 339 B, com 2.080 linhas na homologação; tabelas maiores amortizam "
        "o overhead de página, então o número real tende a ser menor). Reaferir com volume real.",
        "",
        "| Dispositivos | Sensores | Intervalo | Linhas/mês | GB/mês |",
        "|---|---|---|---|---|",
    ]
    for devices, sensors, interval in ((3, 3, 2.0), (100, 6, 5.0), (1000, 6, 10.0)):
        gb = storage_growth_gb_per_month(
            devices=devices, sensors=sensors, interval_s=interval, bytes_per_row=BYTES_PER_ROW
        )
        rows = devices * sensors * (86_400 / interval) * 30
        lines.append(f"| {devices} | {sensors} | {interval:g} s | {rows:,.0f} | {gb:.2f} |")
    lines += [
        "",
        "Sem política de retenção/compactação (não implementada), o disco cresce linearmente: "
        "1 000 dispositivos a cada 10 s enchem 80 GB em poucas semanas. **Retenção de telemetria é trabalho pendente.**",
        "",
        "## O que NÃO está estimado",
        "",
        "- Balanceador, DNS, TLS gerenciado, WAF, banco gerenciado, monitoramento externo, alertas (Alertmanager/pager), "
        "registry privado, suporte, horas de operação, licenças.",
        "- Desempenho de ingestão em escala: o único teste de carga medido é o da API (ver `docs/ops/slo.md`); "
        "a vazão do pipeline MQTT→PostgreSQL **não foi medida**.",
    ]
    return "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"
