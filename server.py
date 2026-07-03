from dataclasses import dataclass, asdict
import json
import socket
import time
import zlib

# ============================================================
# SERVIDOR UDP3 - STOP-AND-WAIT COM SOCKET UDP REAL
# ============================================================
#
# A retransmissão do Stop-and-Wait continua ativa no protocolo, mas os
# cenários abaixo são PERMANENTES: a falha ocorre em TODAS as tentativas,
# então nenhuma retransmissão resolve o problema.
#
# Cenários suportados (definidos no cliente e apenas OBEDECIDOS aqui):
#   PERFEITO                 -> nenhuma falha é simulada
#   PERDA_DADOS_PERMANENTE    -> tratado inteiramente no cliente (o servidor
#                                 nunca chega a receber o pacote)
#   PERDA_ACK_PERMANENTE      -> o servidor entrega a mensagem normalmente,
#                                 mas NUNCA envia o ACK, em nenhuma tentativa
#   ATRASO_DADOS_PERMANENTE    -> tratado no cliente (o atraso sempre
#                                 consome o timeout antes do pacote chegar)
#   ATRASO_ACK_PERMANENTE     -> o servidor atrasa propositalmente o envio
#                                 do ACK em TODAS as tentativas
# ============================================================

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096

# Tempo de atraso proposital do ACK no cenário ATRASO_ACK.
# Deve ser maior que o TIMEOUT configurado no cliente para forçar
# uma retransmissão de forma 100% previsível.
ACK_DELAY_SECONDS = 1.5

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


def show_received_packet(packet: Packet, client_address: tuple[str, int]) -> None:
    """
    Exibe de forma organizada as informações do pacote recebido.
    """
    subtitle("PACOTE DATA RECEBIDO DO CLIENTE")

    print(f"|| Cliente ..................... || {client_address[0]}:{client_address[1]}")
    print(f"|| Tipo do pacote .............. || {packet.kind}")
    print(f"|| Número de sequência ......... || {packet.seq}")
    print(f"|| ACK ......................... || {packet.ack}")
    print(f"|| Mensagem recebida ........... || {packet.payload!r}")
    print(f"|| Checksum recebido ........... || {packet.checksum}")
    print(f"|| Cenário solicitado .......... || {packet.scenario}")
    print(f"|| Tentativa informada ......... || {packet.attempt}")

    separator("-")


def show_delivered_messages(messages: list[str]) -> None:
    """
    Exibe todas as mensagens que já foram entregues à aplicação.
    """
    subtitle("MENSAGENS ENTREGUES À APLICAÇÃO")

    if not messages:
        print("|| Nenhuma mensagem foi entregue ainda.")
    else:
        for index, message in enumerate(messages, start=1):
            print(f"|| {index:02d} || {message}")

    separator("-")


def show_server_status(expected_seq: int, last_valid_ack: int) -> None:
    """
    Exibe o estado atual do protocolo no servidor.
    """
    subtitle("ESTADO ATUAL DO SERVIDOR")

    print(f"|| Sequência esperada agora .... || {expected_seq}")
    print(f"|| Último ACK válido ........... || {last_valid_ack}")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Controle de sequência ....... || Alternância entre 0 e 1")

    separator("-")


def show_start_banner() -> None:
    """
    Exibe o banner inicial do servidor.
    """
    title("SERVIDOR UDP3 INICIADO")

    print(f"|| Endereço de escuta .......... || {HOST}")
    print(f"|| Porta ....................... || {PORT}")
    print(f"|| Buffer ...................... || {BUFFER_SIZE} bytes")
    print(f"|| Atraso proposital de ACK .... || {ACK_DELAY_SECONDS} segundo(s)")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Sequência esperada inicial .. || 0")
    print()
    print("|| O servidor receberá pacotes DATA enviados pelo cliente.")
    print("|| Para cada pacote válido, o servidor enviará um ACK.")
    print("|| O cenário de falha (se houver) é escolhido pelo MENU DO CLIENTE.")
    print("|| Pressione CTRL + C para encerrar o servidor.")

    separator("=")


def show_final_report(messages: list[str]) -> None:
    """
    Exibe o relatório final quando o servidor é encerrado.
    """
    title("SERVIDOR UDP3 ENCERRADO")

    print(f"|| Total de mensagens entregues || {len(messages)}")
    separator("-")

    if not messages:
        print("|| Nenhuma mensagem foi entregue à aplicação.")
    else:
        for index, message in enumerate(messages, start=1):
            print(f"|| {index:02d} || {message}")

    separator("=")


# ============================================================
# CHECKSUM
# ============================================================

def calculate_checksum(kind: str, seq: int, ack: int, payload: str) -> int:
    """
    Calcula o checksum CRC32 usando tipo, sequência, ACK e payload.
    """
    raw_data = f"{kind}|{seq}|{ack}|{payload}".encode("utf-8")
    return zlib.crc32(raw_data) & 0xFFFFFFFF


def make_ack_packet(ack: int, scenario: str, attempt: int) -> Packet:
    """
    Cria um pacote ACK para confirmar o recebimento de um DATA.
    """
    checksum = calculate_checksum("ACK", -1, ack, "")

    subtitle("CRIAÇÃO DO PACOTE ACK")

    log("SERVIDOR", f"Criando pacote ACK para confirmar a sequência {ack}.")
    log("ACK", "Tipo: ACK")
    log("ACK", "Seq: -1")
    log("ACK", f"Ack: {ack}")
    log("ACK", "Payload: ''")
    log("CHECKSUM", f"Checksum calculado com CRC32: {checksum}")

    return Packet(
        kind="ACK",
        seq=-1,
        ack=ack,
        payload="",
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
        log("CHECKSUM", "Checksum inválido.")
        log("CHECKSUM", "O pacote foi alterado ou chegou corrompido.")
        log("CHECKSUM", f"Checksum recebido: {packet.checksum}")
        log("CHECKSUM", f"Checksum esperado: {expected_checksum}")
        return True

    log("CHECKSUM", "Checksum válido. O pacote chegou íntegro.")
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
# ENVIO DO ACK (COM SUPORTE A CENÁRIOS DETERMINÍSTICOS)
# ============================================================

def send_ack(sock: socket.socket, client_address: tuple[str, int], packet: Packet) -> None:
    """
    Envia um ACK ao cliente usando socket UDP real.

    Reage ao cenário informado pelo pacote DATA que originou este ACK:
      - PERDA_ACK_PERMANENTE em QUALQUER tentativa: o ACK NUNCA é enviado.
        Nenhuma retransmissão resolve, e a mensagem nunca é confirmada.
      - ATRASO_ACK_PERMANENTE em QUALQUER tentativa: o envio do ACK é
        sempre atrasado além do timeout do cliente, então nenhuma
        retransmissão resolve.
      - Qualquer outro caso (ex.: PERFEITO): o ACK é enviado normalmente
        e imediatamente.
    """
    subtitle("ENVIO DO ACK PELO SOCKET UDP")

    log("SERVIDOR", f"Preparando envio do ACK {packet.ack}.")
    log("UDP", f"Destino do ACK: {client_address[0]}:{client_address[1]}")
    log("CENÁRIO", f"Cenário ativo para este envio: {packet.scenario} (tentativa {packet.attempt})")

    if packet.scenario == "PERDA_ACK_PERMANENTE":
        log("SIMULAÇÃO", "Cenário PERDA_ACK_PERMANENTE ativo.")
        log("SIMULAÇÃO", "O ACK NÃO será enviado, em NENHUMA tentativa.")
        log("PROTOCOLO", "O cliente nunca receberá confirmação para esta mensagem.")
        return

    if packet.scenario == "ATRASO_ACK_PERMANENTE":
        log("SIMULAÇÃO", "Cenário ATRASO_ACK_PERMANENTE ativo.")
        log("SIMULAÇÃO", f"O envio do ACK será atrasado propositalmente em {ACK_DELAY_SECONDS}s, em TODA tentativa.")
        log("PROTOCOLO", "Isso deverá ser suficiente para estourar o timeout do cliente sempre.")
        time.sleep(ACK_DELAY_SECONDS)
        log("SIMULAÇÃO", "Atraso concluído. Enviando o ACK (agora atrasado) ao cliente.")

    encoded_packet = encode_packet(packet)
    sock.sendto(encoded_packet, client_address)

    log("UDP", "ACK enviado via socket UDP real.")
    log("UDP", f"Bytes enviados: {len(encoded_packet)}")


# ============================================================
# SERVIDOR UDP
# ============================================================

def main() -> None:
    expected_seq = 0
    last_valid_ack = 1
    delivered_messages: list[str] = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))

        show_start_banner()
        show_server_status(expected_seq, last_valid_ack)

        try:
            while True:
                title("AGUARDANDO PACOTE DO CLIENTE")

                log("SERVIDOR", f"Aguardando pacote DATA com sequência esperada {expected_seq}.")
                log("UDP", f"Servidor escutando em {HOST}:{PORT}.")
                log("UDP", "O servidor está bloqueado em recvfrom(), esperando um datagrama UDP.")

                data, client_address = server_socket.recvfrom(BUFFER_SIZE)

                subtitle("DATAGRAMA UDP RECEBIDO")

                log("UDP", f"Datagrama recebido de {client_address[0]}:{client_address[1]}.")
                log("UDP", f"Bytes recebidos: {len(data)}")
                log("SERVIDOR", "Tentando decodificar o datagrama recebido como JSON.")

                try:
                    packet = decode_packet(data)
                except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                    log("SERVIDOR", "Não foi possível decodificar o datagrama recebido.")
                    log("SERVIDOR", "Pacote ignorado.")
                    continue

                show_received_packet(packet, client_address)

                subtitle("VERIFICAÇÃO DE INTEGRIDADE")

                log("SERVIDOR", "Verificando integridade do pacote com CRC32.")

                if is_corrupt(packet):
                    log("SERVIDOR", "Pacote descartado por corrupção.")
                    log("SERVIDOR", f"Reenviando último ACK válido: {last_valid_ack}.")
                    send_ack(server_socket, client_address,
                             make_ack_packet(last_valid_ack, packet.scenario, packet.attempt))
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                subtitle("VALIDAÇÃO DO TIPO DE PACOTE")

                if packet.kind != "DATA":
                    log("SERVIDOR", f"Tipo de pacote inválido: {packet.kind}.")
                    log("SERVIDOR", "O servidor esperava um pacote do tipo DATA.")
                    log("SERVIDOR", "Pacote ignorado.")
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                log("SERVIDOR", "Tipo de pacote válido: DATA.")

                subtitle("VALIDAÇÃO DO NÚMERO DE SEQUÊNCIA")

                if packet.seq != expected_seq:
                    log("SERVIDOR", "Pacote duplicado ou fora de ordem detectado.")
                    log("SERVIDOR", f"Sequência recebida: {packet.seq}.")
                    log("SERVIDOR", f"Sequência esperada: {expected_seq}.")
                    log("APLICAÇÃO", "A mensagem não será entregue novamente.")
                    log("SERVIDOR", f"Reenviando ACK {last_valid_ack} para confirmar o último pacote válido.")

                    send_ack(server_socket, client_address,
                             make_ack_packet(last_valid_ack, packet.scenario, packet.attempt))
                    show_server_status(expected_seq, last_valid_ack)
                    continue

                log("SERVIDOR", "Número de sequência correto.")
                log("SERVIDOR", f"Sequência recebida: {packet.seq}.")
                log("SERVIDOR", f"Sequência esperada: {expected_seq}.")

                title("MENSAGEM RECEBIDA E ENTREGUE")

                log("SERVIDOR", "Pacote correto recebido.")
                log("SERVIDOR", "Entregando dados para a camada de aplicação.")
                log("APLICAÇÃO", f"Mensagem enviada pelo cliente: {packet.payload!r}")

                delivered_messages.append(packet.payload)

                last_valid_ack = packet.seq

                subtitle("ATUALIZAÇÃO DO PROTOCOLO")

                log("PROTOCOLO", f"Último ACK válido atualizado para {last_valid_ack}.")
                log("PROTOCOLO", f"O servidor enviará ACK {packet.seq} ao cliente.")

                send_ack(server_socket, client_address,
                         make_ack_packet(packet.seq, packet.scenario, packet.attempt))

                expected_seq = 1 - expected_seq

                log("PROTOCOLO", f"Próximo pacote esperado agora possui sequência {expected_seq}.")

                show_delivered_messages(delivered_messages)
                show_server_status(expected_seq, last_valid_ack)

        except KeyboardInterrupt:
            show_final_report(delivered_messages)


if __name__ == "__main__":
    main()