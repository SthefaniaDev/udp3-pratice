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


# ============================================================
# CLIENTE UDP COM STOP-AND-WAIT
# ============================================================


class UdpReliableClient:
    def __init__(self, server_host: str, server_port: int, timeout: float):
        self.server_address = (server_host, server_port)
        self.timeout = timeout
        self.seq = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


        title("CLIENTE UDP3 INICIADO")
        log("CLIENTE", f"Servidor configurado em {server_host}:{server_port}.")
        log("CLIENTE", f"Timeout configurado em {timeout} segundo(s).")
        log("CLIENTE", "Modo de envio: Stop-and-Wait.")
        log("CLIENTE", "O cliente envia um pacote e aguarda o ACK antes do próximo.")
        log("PROTOCOLO", "O número de sequência alterna entre 0 e 1.")


    def close(self) -> None:
        self.sock.close()
        title("CLIENTE ENCERRADO")
        log("CLIENTE", "Socket UDP do cliente fechado.")


    def _drain_stray_packets(self) -> None:
        """
        Descarta quaisquer datagramas atrasados que ainda possam chegar
        depois que uma mensagem já foi concluída (comum nos cenários de
        atraso), evitando que "contaminem" o próximo envio.
        """
        self.sock.settimeout(0)
        drained = 0
        try:
            while True:
                self.sock.recvfrom(BUFFER_SIZE)
                drained += 1
        except (BlockingIOError, socket.timeout):
            pass
        finally:
            self.sock.settimeout(None)


        if drained:
            subtitle("LIMPEZA DE PACOTES RESIDUAIS")
            log("CLIENTE", f"{drained} pacote(s) atrasado(s) descartado(s) do buffer.")
            log("PROTOCOLO", "Isso evita que respostas atrasadas afetem o próximo envio.")


    def send(self, payload: str, scenario: str = "PERFEITO") -> bool:
        """
        Envia uma mensagem ao servidor usando UDP com controle de confiabilidade.


        Retorna:
        - True: se a mensagem foi confirmada por ACK.
        - False: se a mensagem não foi confirmada após o limite de tentativas.
        """
        if not payload.strip():
            log("CLIENTE", "Mensagem vazia não pode ser enviada.")
            return False


        title("NOVA MENSAGEM DA APLICAÇÃO")
        log("APLICAÇÃO", f"Mensagem digitada pelo usuário: {payload!r}")
        log("PROTOCOLO", f"Sequência atual do cliente: {self.seq}")
        log("PROTOCOLO", f"Cenário de demonstração escolhido: {scenario}")
        log("PROTOCOLO", f"Limite máximo de tentativas: {MAX_ATTEMPTS}")


        attempt = 1


        try:
            while attempt <= MAX_ATTEMPTS:
                subtitle(f"TENTATIVA {attempt} DE {MAX_ATTEMPTS} || ENVIO DA SEQUÊNCIA {self.seq}")


                log("PROTOCOLO", f"Iniciando tentativa {attempt} de envio.")
                log("PROTOCOLO", "Enquanto o ACK correto não chegar, o pacote poderá ser retransmitido.")


                packet = make_data_packet(self.seq, payload, scenario, attempt)


                # O timer do timeout começa a contar ANTES do envio, pois no
                # cenário de "atraso de dados" o atraso ocorre justamente
                # durante o envio (simulando atraso de rede em trânsito).
                deadline = time.monotonic() + self.timeout


                send_data(self.sock, self.server_address, packet)


                subtitle("ESPERA PELO ACK")
                log("CLIENTE", f"Aguardando ACK {self.seq}.")
                log("TIMEOUT", f"Tempo máximo de espera por tentativa: {self.timeout} segundo(s).")
                log("PROTOCOLO", "Se o ACK não chegar no prazo, essa tentativa será considerada falha.")


                timed_out = False


                while True:
                    remaining_time = deadline - time.monotonic()


                    if remaining_time <= 0:
                        log("TIMEOUT", f"ACK {self.seq} não chegou dentro do tempo limite.")
                        log("PROTOCOLO", "Essa tentativa falhou. O cliente tentará novamente, se ainda houver tentativas.")
                        timed_out = True
                        break


                    self.sock.settimeout(remaining_time)


                    try:
                        data, server_address = self.sock.recvfrom(BUFFER_SIZE)


                    except socket.timeout:
                        log("TIMEOUT", f"ACK {self.seq} não chegou dentro do tempo limite.")
                        log("PROTOCOLO", "Essa tentativa falhou. O cliente tentará novamente, se ainda houver tentativas.")
                        timed_out = True
                        break


                    except ConnectionResetError:
                        log("ERRO", "O sistema informou que o destino UDP recusou ou não respondeu.")
                        log("ERRO", "Isso pode acontecer se o servidor não estiver rodando ou se a porta estiver incorreta.")
                        log("PROTOCOLO", "Tratando como perda de ACK.")
                        timed_out = True
                        break


                    subtitle("ACK RECEBIDO")
                    log("UDP", f"Datagrama recebido de {server_address}.")
                    log("UDP", f"Bytes recebidos: {len(data)}")


                    try:
                        ack_packet = decode_packet(data)
                    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                        log("CLIENTE", "Não foi possível decodificar o ACK recebido.")
                        log("CLIENTE", "O cliente continuará esperando um ACK válido até o timeout.")
                        continue


                    log("CLIENTE", "ACK decodificado com sucesso.")
                    log("ACK", f"Tipo: {ack_packet.kind}")
                    log("ACK", f"Seq: {ack_packet.seq}")
                    log("ACK", f"Ack: {ack_packet.ack}")
                    log("ACK", f"Payload: {ack_packet.payload!r}")
                    log("ACK", f"Checksum: {ack_packet.checksum}")


                    log("CLIENTE", "Verificando integridade do ACK com CRC32...")


                    if is_corrupt(ack_packet):
                        log("CLIENTE", "ACK descartado por corrupção.")
                        log("PROTOCOLO", "O cliente continuará aguardando até timeout ou ACK válido.")
                        continue


                    if ack_packet.kind != "ACK":
                        log("CLIENTE", f"Tipo de pacote inesperado: {ack_packet.kind}.")
                        log("CLIENTE", "O cliente esperava um pacote do tipo ACK.")
                        continue


                    if ack_packet.ack != self.seq:
                        log("CLIENTE", f"ACK inesperado recebido: {ack_packet.ack}.")
                        log("CLIENTE", f"ACK esperado: {self.seq}.")
                        log("PROTOCOLO", "Esse ACK pode ser duplicado, atrasado ou referente a outro pacote.")
                        log("PROTOCOLO", "O cliente continuará esperando o ACK correto.")
                        continue


                    title("PACOTE CONFIRMADO COM SUCESSO")
                    log("CLIENTE", f"ACK {ack_packet.ack} recebido corretamente.")
                    log("PROTOCOLO", f"Pacote seq={self.seq} confirmado pelo servidor.")
                    log("RESULTADO", "Mensagem enviada com sucesso.")


                    self.seq = 1 - self.seq


                    log("PROTOCOLO", f"Alternando número de sequência. Próximo pacote usará seq={self.seq}.")
                    return True


                if timed_out:
                    attempt += 1


            title("ENVIO NÃO CONFIRMADO")
            log("ERRO", f"A mensagem não foi confirmada após {MAX_ATTEMPTS} tentativa(s).")
            log("ERRO", "Envio considerado sem sucesso.")
            log("PROTOCOLO", "O cliente desistiu dessa mensagem para evitar loop infinito.")
            log("PROTOCOLO", f"A sequência atual continuará sendo {self.seq}, pois não houve ACK válido.")
            log("MENU", "Você pode tentar enviar a mesma mensagem novamente pelo menu.")


            return False
        finally:
            self._drain_stray_packets()

# ============================================================
# MENU INTERATIVO DO CLIENTE
# ============================================================


def show_menu() -> None:
    title("CLIENTE UDP3 - MENU PRINCIPAL")
    print("|| ---------------- CENÁRIOS DE DEMONSTRAÇÃO ---------------- ||")
    print("|| 1 || Caso perfeito")
    print("|| 2 || Perda de dados ")
    print("|| 3 || Perda de ACK ")
    print("|| 4 || Atraso de dados ")
    print("|| 5 || Atraso de ACK ")
    print("|| ------------------------------------------------------------ ||")
    print("|| 6 || Enviar mensagem livre (sem falha simulada)")
    print("|| 7 || Ver configurações do cliente")
    print("|| 8 || Explicar funcionamento da prática")
    print("|| 0 || Encerrar cliente")
    separator("=")




def show_settings() -> None:
    title("CONFIGURAÇÕES DO CLIENTE")
    print(f"|| Servidor .................... || {SERVER_HOST}:{SERVER_PORT}")
    print(f"|| Tamanho do buffer ........... || {BUFFER_SIZE} bytes")
    print(f"|| Timeout ..................... || {TIMEOUT} segundo(s)")
    print(f"|| Máximo de tentativas ........ || {MAX_ATTEMPTS}")
    print(f"|| Atraso proposital de DATA ... || {DATA_DELAY_SECONDS} segundo(s)")
    print(f"|| Protocolo ................... || UDP + Stop-and-Wait")
    print(f"|| Sequência ................... || Alternância entre 0 e 1")
    print(f"|| Modo de simulação ........... || Determinístico (via menu, sem sorteio)")
    separator("=")




def explain_practice() -> None:
    title("EXPLICAÇÃO DA PRÁTICA UDP3")


    print("|| Esta prática usa sockets UDP reais em Python.")
    print("|| O cliente envia mensagens para um servidor UDP.")
    print("|| Como o UDP não garante entrega, foram adicionados controles manuais.")
    print()


    print("|| MECANISMOS IMPLEMENTADOS")
    print("|| - Checksum CRC32 para detectar corrupção.")
    print("|| - ACK para confirmar recebimento.")
    print("|| - Timeout para detectar ausência de resposta.")
    print("|| - Retransmissão quando o ACK não chega.")
    print("|| - Limite de tentativas para evitar loop infinito.")
    print("|| - Número de sequência alternando entre 0 e 1.")
    print()


    print("|| CENÁRIOS DISPONÍVEIS NO MENU")
    print("|| 1) Perfeito                  -> DATA e ACK chegam normalmente.")
    print("|| 2) Perda de dados permanente -> o DATA nunca chega ao servidor.")
    print("|| 3) Perda de ACK permanente   -> o ACK nunca chega ao cliente.")
    print("|| 4) Atraso de dados permanente -> o DATA sempre chega atrasado.")
    print("|| 5) Atraso de ACK permanente   -> o ACK sempre chega atrasado.")
    print("|| A retransmissão do Stop-and-Wait continua ativa (o cliente")
    print("|| tenta reenviar até MAX_ATTEMPTS vezes), mas como a falha é")
    print("|| PERMANENTE em todos esses cenários, nenhuma retransmissão")
    print("|| resolve: a mensagem acaba NÃO sendo confirmada. Isso demonstra")
    print("|| o limite do protocolo Stop-and-Wait diante de uma falha")
    print("|| persistente na rede.")
    print()


    print("|| OBJETIVO")
    print("|| Mostrar como implementar confiabilidade sobre UDP (RDT 3.0).")
    separator("=")




def read_user_message(default: str) -> str:
    title("DIGITAR MENSAGEM")
    print("|| Digite a mensagem que será enviada ao servidor.")
    print(f"|| Deixe vazio para usar a mensagem padrão: {default!r}")
    separator("-")


    typed = input("Mensagem: ")
    return typed if typed.strip() else default




def run_scenario(client: "UdpReliableClient", scenario_key: str) -> None:
    scenario, description = SCENARIOS[scenario_key]


    title(f"EXECUTANDO CENÁRIO: {description.upper()}")
    log("MENU", f"Cenário selecionado: {scenario}")


    default_message = f"Mensagem de teste - {description}"
    message = read_user_message(default_message)


    success = client.send(message, scenario=scenario)


    if success:
        log("MENU", "A mensagem foi enviada e confirmada com sucesso.")
    else:
        log("MENU", "A mensagem não foi confirmada após o limite de tentativas.")
        log("MENU", "Você pode tentar executar o cenário novamente pelo menu.")


    pause()
