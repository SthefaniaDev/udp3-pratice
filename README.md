
# UDP3 — Cliente e Servidor com Sockets UDP

Este repositório contém uma prática de comunicação entre cliente e servidor utilizando **sockets UDP reais em Python**.

O projeto demonstra o funcionamento do protocolo UDP e implementa mecanismos adicionais de confiabilidade inspirados no **RDT 3.0**, utilizando a estratégia **Stop-and-Wait com bit alternado**.

Como o UDP não garante automaticamente a entrega, a ordem ou a confirmação dos pacotes, foram implementados recursos como ACK, checksum CRC32, timeout, retransmissão, controle de sequência e limite de tentativas.

Além da comunicação normal, o cliente apresenta um menu com cenários determinísticos de perda e atraso de pacotes.

---

## Objetivo da prática

Desenvolver uma aplicação cliente-servidor utilizando sockets UDP reais, demonstrando:

- Comunicação entre cliente e servidor;
- Envio e recebimento de datagramas UDP;
- Criação de pacotes do tipo `DATA`;
- Criação de pacotes de confirmação do tipo `ACK`;
- Uso de checksum CRC32;
- Controle de sequência alternando entre `0` e `1`;
- Timeout para detectar ausência de confirmação;
- Retransmissão de pacotes;
- Limite máximo de tentativas;
- Detecção de pacotes duplicados ou fora de ordem;
- Execução de cenários determinísticos;
- Perda permanente de pacotes DATA;
- Perda permanente de ACK;
- Atraso permanente de pacotes DATA;
- Atraso permanente de ACK;
- Comunicação entre dois computadores diferentes.

---

## Tecnologias utilizadas

- Python;
- Sockets UDP;
- JSON;
- CRC32;
- Dataclasses;
- Stop-and-Wait;
- Alternating Bit Protocol;
- Conceitos do RDT 3.0.

---

## Estrutura do projeto

```text
udp3-pratice/
│
├── client.py
├── server.py
└── README.md
```

---

## Descrição dos arquivos

### `client.py`

Arquivo responsável pela execução do cliente UDP.

O cliente realiza as seguintes funções:

- Cria um socket UDP real;
- Exibe um menu interativo;
- Permite escolher o cenário da demonstração;
- Permite digitar mensagens manualmente;
- Cria pacotes do tipo `DATA`;
- Calcula o checksum CRC32;
- Converte os pacotes para JSON e bytes;
- Envia os pacotes para o servidor;
- Aguarda o recebimento do ACK;
- Verifica a integridade do ACK recebido;
- Controla o timeout;
- Retransmite o pacote quando o ACK não chega;
- Limita o envio a cinco tentativas;
- Alterna o número de sequência entre `0` e `1`;
- Descarta respostas atrasadas que tenham permanecido no buffer;
- Simula perda e atraso de pacotes DATA;
- Informa ao servidor os cenários relacionados ao ACK.

### `server.py`

Arquivo responsável pela execução do servidor UDP.

O servidor realiza as seguintes funções:

- Cria um socket UDP real;
- Escuta a porta configurada;
- Recebe pacotes enviados pelo cliente;
- Decodifica os datagramas recebidos;
- Verifica o checksum CRC32;
- Valida o tipo do pacote;
- Verifica o número de sequência;
- Detecta pacotes duplicados ou fora de ordem;
- Entrega mensagens válidas à aplicação;
- Mantém uma lista das mensagens entregues;
- Cria pacotes do tipo `ACK`;
- Envia confirmações ao cliente;
- Simula perda permanente de ACK;
- Simula atraso permanente de ACK;
- Exibe o estado atual do protocolo;
- Apresenta um relatório final ao ser encerrado.

---

## Estrutura dos pacotes

Os pacotes utilizados na comunicação possuem a seguinte estrutura:

```python
@dataclass
class Packet:
    kind: str
    seq: int
    ack: int
    payload: str
    checksum: int
    scenario: str = "PERFEITO"
    attempt: int = 1
```

### Campos do pacote

| Campo | Descrição |
|---|---|
| `kind` | Tipo do pacote: `DATA` ou `ACK` |
| `seq` | Número de sequência do pacote DATA |
| `ack` | Número de confirmação do pacote ACK |
| `payload` | Conteúdo da mensagem |
| `checksum` | Valor CRC32 usado para verificar integridade |
| `scenario` | Cenário escolhido no menu do cliente |
| `attempt` | Número da tentativa atual |

---

## Pacote DATA

O pacote `DATA` é criado pelo cliente para transportar a mensagem.

Exemplo:

```text
Tipo: DATA
Sequência: 0
ACK: -1
Mensagem: 'Olá, servidor'
Cenário: PERFEITO
Tentativa: 1
```

O campo `ack` recebe o valor `-1` porque não é utilizado em pacotes do tipo `DATA`.

---

## Pacote ACK

O pacote `ACK` é criado pelo servidor para confirmar o recebimento de um pacote DATA.

Exemplo:

```text
Tipo: ACK
Sequência: -1
ACK: 0
Payload: ''
```

O campo `seq` recebe o valor `-1` porque o pacote ACK não transporta uma nova mensagem.

O campo `ack` informa qual número de sequência está sendo confirmado.

---

## Funcionamento da comunicação

A comunicação acontece da seguinte forma:

1. O servidor é iniciado e permanece aguardando datagramas UDP.
2. O cliente é iniciado.
3. O usuário escolhe um cenário no menu.
4. O usuário digita uma mensagem.
5. O cliente cria um pacote do tipo `DATA`.
6. O pacote recebe um número de sequência, que pode ser `0` ou `1`.
7. O cliente calcula o checksum CRC32.
8. O cenário escolhido é incluído no pacote.
9. O cliente envia o pacote ao servidor.
10. O servidor recebe e decodifica o datagrama.
11. O servidor verifica o checksum.
12. O servidor valida o tipo e a sequência do pacote.
13. Se o pacote for válido, a mensagem é entregue à aplicação.
14. O servidor cria um pacote ACK.
15. O ACK é enviado ao cliente.
16. O cliente recebe e valida o ACK.
17. Se o ACK for correto, a mensagem é considerada confirmada.
18. Cliente e servidor alternam o controle de sequência.
19. Se o ACK não chegar, o cliente realiza uma nova tentativa.
20. Após cinco tentativas sem confirmação, o envio é encerrado como não confirmado.

---

## Mecanismos de confiabilidade

### Checksum CRC32

O checksum CRC32 é utilizado para verificar a integridade dos pacotes.

Ele é calculado utilizando:

- Tipo do pacote;
- Número de sequência;
- Número de ACK;
- Conteúdo da mensagem.

```python
raw_data = f"{kind}|{seq}|{ack}|{payload}".encode("utf-8")
checksum = zlib.crc32(raw_data) & 0xFFFFFFFF
```

O receptor recalcula o checksum e compara com o valor recebido.

Se os valores forem diferentes, o pacote é considerado corrompido.

---

### ACK

O ACK é uma confirmação enviada pelo servidor ao cliente.

Exemplos:

```text
ACK 0
ACK 1
```

Se o cliente enviar um pacote com sequência `0`, ele espera receber um ACK com valor `0`.

Se enviar um pacote com sequência `1`, espera receber um ACK com valor `1`.

---

### Timeout

O cliente aguarda o ACK durante um tempo definido:

```python
TIMEOUT = 0.8
```

Isso significa que cada tentativa possui um prazo de `0,8` segundo.

Se o ACK não for recebido dentro desse período, a tentativa é considerada falha.

---

### Retransmissão

Quando ocorre timeout, o cliente retransmite o pacote.

A retransmissão mantém:

- A mesma mensagem;
- O mesmo número de sequência;
- O mesmo cenário;
- Um novo número de tentativa.

---

### Limite de tentativas

O cliente possui um limite máximo de tentativas:

```python
MAX_ATTEMPTS = 5
```

Se nenhum ACK válido for recebido após cinco tentativas, a mensagem é considerada não confirmada.

Exemplo:

```text
========================================================================
||                         ENVIO NÃO CONFIRMADO                        ||
========================================================================
[ERRO] A mensagem não foi confirmada após 5 tentativa(s).
[ERRO] Envio considerado sem sucesso.
[PROTOCOLO] O cliente desistiu dessa mensagem para evitar loop infinito.
```

---

### Número de sequência

Os pacotes utilizam números de sequência alternando entre `0` e `1`.

```text
0 → 1 → 0 → 1
```

Esse controle permite identificar:

- Pacotes duplicados;
- Pacotes fora de ordem;
- ACKs inesperados;
- Retransmissões de mensagens já recebidas.

Após receber e confirmar corretamente um pacote, o cliente executa:

```python
self.seq = 1 - self.seq
```

O servidor também alterna a sequência esperada:

```python
expected_seq = 1 - expected_seq
```

---

### Detecção de pacotes duplicados

Um pacote pode ser retransmitido porque o ACK foi perdido ou atrasado.

Nesse caso, o servidor pode receber novamente uma mensagem que já foi entregue.

O servidor compara a sequência recebida com a sequência esperada.

Se forem diferentes, o pacote é considerado duplicado ou fora de ordem.

```text
[SERVIDOR] Pacote duplicado ou fora de ordem detectado.
[APLICAÇÃO] A mensagem não será entregue novamente.
[SERVIDOR] Reenviando ACK do último pacote válido.
```

Dessa forma, a mesma mensagem não é adicionada duas vezes à aplicação.

---

## Cenários de demonstração

Os cenários não são escolhidos aleatoriamente.

O usuário seleciona no menu do cliente exatamente qual situação deseja demonstrar.

Os cenários são definidos da seguinte forma:

```python
SCENARIOS = {
    "1": ("PERFEITO", "Caso perfeito"),
    "2": ("PERDA_DADOS_PERMANENTE", "Perda de dados"),
    "3": ("PERDA_ACK_PERMANENTE", "Perda de ACK"),
    "4": ("ATRASO_DADOS_PERMANENTE", "Atraso de dados"),
    "5": ("ATRASO_ACK_PERMANENTE", "Atraso de ACK"),
}
```

---

## Situação 1 — Caso perfeito

Neste cenário, nenhuma falha é simulada.

O fluxo ocorre normalmente:

```text
Cliente envia DATA
        ↓
Servidor recebe DATA
        ↓
Servidor entrega a mensagem
        ↓
Servidor envia ACK
        ↓
Cliente recebe o ACK
        ↓
Mensagem confirmada
```

Exemplo no cliente:

```text
[UDP] Pacote DATA enviado via socket UDP real.
[CHECKSUM] Checksum válido. O ACK chegou íntegro.
[CLIENTE] ACK recebido corretamente.
[RESULTADO] Mensagem enviada com sucesso.
```

Exemplo no servidor:

```text
========================================================================
||                    MENSAGEM RECEBIDA E ENTREGUE                    ||
========================================================================
[APLICAÇÃO] Mensagem enviada pelo cliente: 'Olá, servidor'
```

---

## Situação 2 — Perda de dados

Neste cenário, o pacote DATA não é enviado pelo cliente.

A perda ocorre dentro da função `send_data()`:

```python
if packet.scenario == "PERDA_DADOS_PERMANENTE":
    return
```

O servidor não recebe a mensagem e, consequentemente, não envia ACK.

Fluxo:

```text
Cliente cria DATA
        ↓
Cliente simula a perda
        ↓
DATA não é enviado
        ↓
Servidor não recebe nada
        ↓
Cliente aguarda o ACK
        ↓
Ocorre timeout
        ↓
Cliente retransmite
```

Como a perda é permanente, todas as cinco tentativas falham.

---

## Situação 3 — Perda de ACK

Neste cenário, o cliente envia normalmente o pacote DATA.

O servidor recebe, valida e entrega a mensagem à aplicação, mas não envia o ACK.

A perda ocorre no servidor:

```python
if packet.scenario == "PERDA_ACK_PERMANENTE":
    return
```

Fluxo:

```text
Cliente envia DATA
        ↓
Servidor recebe DATA
        ↓
Servidor entrega a mensagem
        ↓
Servidor cria o ACK
        ↓
ACK não é enviado
        ↓
Cliente dá timeout
        ↓
Cliente retransmite
```

Nesse cenário, a mensagem pode ter sido entregue pelo servidor, mesmo que o cliente não tenha recebido a confirmação.

---

## Situação 4 — Atraso de dados

Neste cenário, o cliente segura o pacote DATA antes de realizar o envio.

O tempo de atraso é:

```python
DATA_DELAY_SECONDS = 1.5
```

O timeout do cliente é:

```python
TIMEOUT = 0.8
```

Como o atraso é maior que o timeout, a tentativa expira.

```python
time.sleep(DATA_DELAY_SECONDS)
```

Fluxo:

```text
Cliente cria DATA
        ↓
Cliente segura o pacote por 1,5 segundo
        ↓
Timeout configurado em 0,8 segundo
        ↓
Pacote é enviado atrasado
        ↓
Tentativa é considerada expirada
```

O atraso é uma simulação realizada antes do envio pelo socket.

---

## Situação 5 — Atraso de ACK

Neste cenário, o servidor recebe e entrega a mensagem normalmente.

Porém, ele espera antes de enviar o ACK.

O tempo de atraso é:

```python
ACK_DELAY_SECONDS = 1.5
```

Como esse valor é maior que o timeout do cliente, o cliente considera que a tentativa expirou antes de receber a confirmação.

```python
time.sleep(ACK_DELAY_SECONDS)
```

Fluxo:

```text
Cliente envia DATA
        ↓
Servidor recebe DATA
        ↓
Servidor entrega a mensagem
        ↓
Servidor segura o ACK por 1,5 segundo
        ↓
Cliente dá timeout em 0,8 segundo
        ↓
Servidor envia o ACK atrasado
```

---

## Menu do cliente

Ao executar o cliente, será apresentado o seguinte menu:

```text
========================================================================
||                    CLIENTE UDP3 - MENU PRINCIPAL                    ||
========================================================================
|| ---------------- CENÁRIOS DE DEMONSTRAÇÃO ---------------- ||
|| 1 || Caso perfeito
|| 2 || Perda de dados
|| 3 || Perda de ACK
|| 4 || Atraso de dados
|| 5 || Atraso de ACK
|| ------------------------------------------------------------ ||
|| 6 || Enviar mensagem livre (sem falha simulada)
|| 7 || Ver configurações do cliente
|| 8 || Explicar funcionamento da prática
|| 0 || Encerrar cliente
========================================================================
```

### Opção 1 — Caso perfeito

Executa uma comunicação sem falhas simuladas.

### Opção 2 — Perda de dados

Impede permanentemente o envio do pacote DATA.

### Opção 3 — Perda de ACK

O servidor recebe a mensagem, mas não envia a confirmação.

### Opção 4 — Atraso de dados

Atrasa o pacote DATA por um tempo maior que o timeout.

### Opção 5 — Atraso de ACK

Atrasa a confirmação enviada pelo servidor.

### Opção 6 — Mensagem livre

Permite enviar uma mensagem sem falha simulada.

### Opção 7 — Configurações

Exibe:

- IP do servidor;
- Porta;
- Tamanho do buffer;
- Timeout;
- Máximo de tentativas;
- Tempo de atraso;
- Protocolo utilizado;
- Modo de simulação.

### Opção 8 — Explicação da prática

Exibe uma explicação resumida do funcionamento da comunicação.

### Opção 0 — Encerrar

Fecha o socket e encerra o cliente.

---

## Requisitos

Para executar o projeto, é necessário possuir:

- Python 3.9 ou superior;
- Dois terminais;
- Cliente e servidor na mesma rede, caso sejam utilizados dois computadores;
- Porta UDP `5000` liberada no firewall.

Não é necessário instalar bibliotecas externas.

Todas as bibliotecas utilizadas fazem parte da biblioteca padrão do Python.

---

## Como executar o projeto

### 1. Clone o repositório

```bash
git clone URL_DO_REPOSITORIO
```

### 2. Acesse a pasta

```bash
cd udp3-pratice
```

### 3. Execute o servidor

Abra um terminal e execute:

```bash
python server.py
```

Ou:

```bash
python3 server.py
```

No Windows, também pode ser utilizado:

```bash
py server.py
```

O servidor ficará aguardando pacotes na porta `5000`.

### 4. Execute o cliente

Abra outro terminal e execute:

```bash
python client.py
```

Ou:

```bash
python3 client.py
```

No Windows:

```bash
py client.py
```

---

## Executando na mesma máquina

Para executar cliente e servidor no mesmo computador, altere no `client.py`:

```python
SERVER_HOST = "127.0.0.1"
```

O servidor pode continuar usando:

```python
HOST = "0.0.0.0"
```

Depois:

1. Abra um terminal e execute `server.py`;
2. Abra outro terminal e execute `client.py`;
3. Escolha um cenário no menu.

---

## Executando em dois computadores

Para executar o projeto em duas máquinas, os dois computadores precisam estar conectados à mesma rede.

### Computador do servidor

Execute:

```bash
ipconfig
```

Procure pelo endereço IPv4.

Exemplo:

```text
192.168.1.16
```

O servidor deve permanecer configurado assim:

```python
HOST = "0.0.0.0"
PORT = 5000
```

### Computador do cliente

No `client.py`, coloque o IP do servidor:

```python
SERVER_HOST = "192.168.1.16"
SERVER_PORT = 5000
```

Depois, execute primeiro o servidor e, em seguida, o cliente.

---

## Firewall

O firewall do sistema pode bloquear a comunicação UDP.

No computador do servidor, permita o acesso do Python às redes privadas.

Também é necessário garantir que a porta UDP `5000` esteja liberada.

Para verificar se as máquinas estão na mesma rede, execute no cliente:

```bash
ping 192.168.1.16
```

Substitua o endereço pelo IP real do servidor.

---

## Reinicialização entre cenários

Os cenários de falha foram desenvolvidos para serem persistentes.

Em situações como perda de ACK ou atraso de pacotes, o servidor pode ter recebido e entregado a mensagem mesmo que o cliente não tenha recebido a confirmação.

Isso pode deixar cliente e servidor com estados de sequência diferentes.

Por esse motivo, recomenda-se executar cada cenário separadamente.

Após concluir um cenário:

1. Encerre o cliente pela opção `0`;
2. Encerre o servidor com `CTRL + C`;
3. Aguarde alguns segundos nos cenários de atraso;
4. Inicie novamente o servidor;
5. Inicie novamente o cliente;
6. Execute o próximo cenário.

Ao reiniciar:

```text
Cliente: sequência inicial = 0
Servidor: sequência esperada = 0
Último ACK válido = 1
```

Isso garante que cada demonstração comece com o protocolo sincronizado.

---

## Diferença entre TCP e UDP

O TCP oferece automaticamente:

- Estabelecimento de conexão;
- Confirmação de recebimento;
- Controle de ordem;
- Retransmissão;
- Controle de fluxo;
- Detecção de perda.

O UDP não oferece essas garantias por padrão.

Nesta prática, parte desses mecanismos foi implementada manualmente sobre o UDP.

---

## Por que utilizar UDP?

O UDP possui menor sobrecarga e não exige o estabelecimento de conexão.

Ele é usado principalmente em aplicações nas quais velocidade e baixa latência são importantes, como:

- Jogos online;
- Chamadas de voz e vídeo;
- Transmissões ao vivo;
- DNS;
- Aplicações em tempo real;
- Sistemas de monitoramento.

Quando necessário, a própria aplicação pode implementar mecanismos específicos de confiabilidade.

---

## Roteiro sugerido para demonstração

1. Conecte os dois computadores à mesma rede.
2. Confirme o endereço IPv4 do servidor.
3. Configure o IP em `SERVER_HOST`.
4. Execute o `server.py`.
5. Mostre que o servidor está aguardando pacotes.
6. Execute o `client.py`.
7. Apresente o menu de cenários.
8. Execute o caso perfeito.
9. Mostre o pacote DATA sendo criado.
10. Mostre o checksum CRC32.
11. Mostre a mensagem chegando ao servidor.
12. Mostre a criação e o envio do ACK.
13. Mostre o cliente confirmando a mensagem.
14. Reinicie cliente e servidor.
15. Execute o cenário de perda de dados.
16. Mostre o timeout e as retransmissões.
17. Reinicie cliente e servidor.
18. Execute o cenário de perda de ACK.
19. Mostre que o servidor entrega a mensagem, mas o cliente não recebe confirmação.
20. Reinicie cliente e servidor.
21. Execute o atraso de dados.
22. Reinicie cliente e servidor.
23. Execute o atraso de ACK.
24. Mostre o limite de cinco tentativas.
25. Encerre o cliente pela opção `0`.
26. Encerre o servidor com `CTRL + C`.

---

## Observações

Este projeto possui finalidade acadêmica e didática.

Os cenários de falha são simulados diretamente pelo código para tornar os resultados previsíveis durante a apresentação.

O projeto não substitui um protocolo completo de transporte confiável, mas demonstra os principais conceitos de:

- Confirmação;
- Timeout;
- Retransmissão;
- Integridade;
- Sequenciamento;
- Detecção de duplicidade;
- Comunicação cliente-servidor com UDP.
````
