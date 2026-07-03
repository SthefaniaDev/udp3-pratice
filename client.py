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

# ============================================================
# CHECKSUM
# ============================================================


def calculate_checksum(kind: str, seq: int, ack: int, payload: str) -> int:
    """
    Calcula o checksum CRC32 usando tipo, sequência, ACK e payload.
    """
    raw_data = f"{kind}|{seq}|{ack}|{payload}".encode("utf-8")
    return zlib.crc32(raw_data) & 0xFFFFFFFF




def make_data_packet(seq: int, payload: str, scenario: str, attempt: int) -> Packet:
    """
    Cria um pacote DATA com número de sequência, mensagem e metadados
    do cenário de demonstração ativo.
    """
    checksum = calculate_checksum("DATA", seq, -1, payload)


    subtitle("CRIAÇÃO DO PACOTE DATA")
    log("CLIENTE", f"Criando pacote DATA.")
    log("PACOTE", f"Tipo: DATA")
    log("PACOTE", f"Sequência: {seq}")
    log("PACOTE", f"ACK: -1")
    log("PACOTE", f"Mensagem: {payload!r}")
    log("PACOTE", f"Cenário: {scenario} (tentativa {attempt})")
    log("CHECKSUM", f"Checksum calculado com CRC32: {checksum}")


    return Packet(
        kind="DATA",
        seq=seq,
        ack=-1,
        payload=payload,
        checksum=checksum,
        scenario=scenario,
        attempt=attempt,
    )




def is_corrupt(packet: Packet) -> bool:
    """
    Verifica se o pacote recebido foi corrompido.
    """
    expected_checksum = calculate_checksum(
        packet.kind,
        packet.seq,
        packet.ack,
        packet.payload
    )


    if packet.checksum != expected_checksum:
        log("CHECKSUM", "Checksum inválido. O ACK foi alterado ou chegou corrompido.")
        log("CHECKSUM", f"Checksum recebido: {packet.checksum}")
        log("CHECKSUM", f"Checksum esperado: {expected_checksum}")
        return True


    log("CHECKSUM", "Checksum válido. O ACK chegou íntegro.")
    return False

# ============================================================
# SERIALIZAÇÃO
# ============================================================


def encode_packet(packet: Packet) -> bytes:
    """
    Converte o pacote para JSON em bytes antes do envio pelo UDP.
    """
    json_packet = json.dumps(asdict(packet))
    return json_packet.encode("utf-8")




def decode_packet(data: bytes) -> Packet:
    """
    Converte bytes recebidos pelo socket UDP em um objeto Packet.
    """
    json_packet = data.decode("utf-8")
    packet_dict = json.loads(json_packet)
    return Packet(**packet_dict)

# ============================================================
# ENVIO DO DATA (COM SUPORTE A CENÁRIOS DETERMINÍSTICOS)
# ============================================================


def send_data(sock: socket.socket, server_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um pacote DATA ao servidor usando socket UDP real.


    Reage ao cenário ativo:
      - PERDA_DADOS_PERMANENTE em QUALQUER tentativa: o pacote NUNCA é
        enviado. Nenhuma retransmissão resolve, e a mensagem acaba não
        sendo confirmada.
      - ATRASO_DADOS_PERMANENTE em QUALQUER tentativa: o envio é sempre
        atrasado além do timeout, então nenhuma retransmissão resolve.
      - Qualquer outro caso (ex.: PERFEITO): o pacote é enviado normalmente
        e imediatamente.
    """
    subtitle("ENVIO DO PACOTE PELO SOCKET UDP")
    log("CLIENTE", f"Preparando envio do pacote seq={packet.seq}.")
    log("UDP", f"Destino configurado: {server_address[0]}:{server_address[1]}")
    log("CENÁRIO", f"Cenário ativo: {packet.scenario} (tentativa {packet.attempt})")


    if packet.scenario == "PERDA_DADOS_PERMANENTE":
        log("SIMULAÇÃO", "Cenário PERDA_DADOS_PERMANENTE ativo.")
        log("SIMULAÇÃO", "O pacote DATA NÃO será enviado, em NENHUMA tentativa.")
        log("PROTOCOLO", "O cliente continuará esperando o ACK até ocorrer timeout.")
        return


    if packet.scenario == "ATRASO_DADOS_PERMANENTE":
        log("SIMULAÇÃO", "Cenário ATRASO_DADOS_PERMANENTE ativo.")
        log("SIMULAÇÃO", f"O envio será atrasado propositalmente em {DATA_DELAY_SECONDS}s, em TODA tentativa.")
        log("PROTOCOLO", "Esse atraso deverá consumir o timeout antes mesmo da resposta.")
        time.sleep(DATA_DELAY_SECONDS)
        log("SIMULAÇÃO", "Atraso concluído. Enviando o pacote (agora atrasado) ao servidor.")


    encoded_packet = encode_packet(packet)
    sock.sendto(encoded_packet, server_address)


    log("UDP", "Pacote DATA enviado via socket UDP real.")
    log("UDP", f"Bytes enviados: {len(encoded_packet)}")


