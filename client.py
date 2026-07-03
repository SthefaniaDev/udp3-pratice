from dataclasses import dataclass, asdict
import json
import socket
import time
import zlib


# ============================================================
# CLIENTE UDP3 - STOP-AND-WAIT COM SOCKET UDP REAL
# ============================================================
#
# O cliente agora executa CENÁRIOS DETERMINÍSTICOS escolhidos pelo
# usuário em um menu, em vez de depender de sorteio aleatório.
#
# A retransmissão do Stop-and-Wait continua ativa no protocolo (o cliente
# sempre tenta reenviar até MAX_ATTEMPTS vezes), mas os cenários de falha
# abaixo são PERMANENTES: a falha ocorre em TODAS as tentativas, então a
# retransmissão nunca resolve o problema e a mensagem acaba não sendo
# confirmada. Isso demonstra o limite do protocolo diante de uma falha
# persistente na rede (ao contrário de uma falha isolada e temporária).
#
#   1) Caso perfeito                        -> nenhuma falha
#   2) Perda de dados (permanente)          -> o DATA nunca chega ao servidor
#   3) Perda de ACK (permanente)            -> o ACK nunca chega ao cliente
#   4) Atraso de dados (permanente)         -> o DATA sempre chega atrasado
#   5) Atraso de ACK (permanente)           -> o ACK sempre chega atrasado
# ============================================================


SERVER_HOST = "192.168.1.16"
SERVER_PORT = 5000
BUFFER_SIZE = 4096
TIMEOUT = 0.8
MAX_ATTEMPTS = 5


# Tempo de atraso proposital do DATA no cenário "Atraso de dados".
# Deve ser maior que o TIMEOUT para forçar uma retransmissão previsível.
DATA_DELAY_SECONDS = 1.5


SCENARIOS = {
    "1": ("PERFEITO", "Caso perfeito (sem falhas)"),
    "2": ("PERDA_DADOS_PERMANENTE", "Perda de dados (permanente - mensagem nunca chega)"),
    "3": ("PERDA_ACK_PERMANENTE", "Perda de ACK (permanente - mensagem nunca é confirmada)"),
    "4": ("ATRASO_DADOS_PERMANENTE", "Atraso de dados (permanente - sempre estoura o timeout)"),
    "5": ("ATRASO_ACK_PERMANENTE", "Atraso de ACK (permanente - sempre estoura o timeout)"),
}


LINE_SIZE = 72




# ============================================================
# ESTRUTURA DO PACOTE
# ============================================================


@dataclass
class Packet:
    kind: str
    seq: int
    ack: int
    payload: str
    checksum: int
    scenario: str = "PERFEITO"
    attempt: int = 1

# ============================================================
# FUNÇÕES AUXILIARES DE FORMATAÇÃO
# ============================================================


def separator(symbol: str = "=") -> None:
    print(symbol * LINE_SIZE)




def title(text: str) -> None:
    print()
    separator("=")
    print(f"|| {text.center(LINE_SIZE - 6)} ||")
    separator("=")




def subtitle(text: str) -> None:
    print()
    separator("-")
    print(f"|| {text}")
    separator("-")




def log(section: str, message: str) -> None:
    """
    Exibe mensagens padronizadas para facilitar a apresentação da prática.
    """
    print(f"[{section}] {message}")




def pause() -> None:
    input("\nPressione ENTER para continuar...")
