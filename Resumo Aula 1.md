# RESUMO AULA 1 BOOTCAMP - NEARX - FEV/2024

## WALLET

### Funções de Hash 

Eu gosto muito desse site para explicar o que é uma Hash.
Nele você digita uma informação, e já aparece um hash usando o algoritmo sha256.
Basta mudar, colocando " . " ou um espaço mesmo, e você entenderá o conceito de avalanche, determinístico, resistente à colisão, fácil de computar, impossibilidade de reverter.

[Exemplo de Hash com SHA256](https://tools.superdatascience.com/blockchain/hash/)

Neste mesmo site é possível entender o conceito de bloco e nonce:

[Entendendo o Bloco e o Nonce](https://tools.superdatascience.com/blockchain/block;)

Posteriormente, o conceito de Blockchain:

[Conceito Básico de uma Blockchain](https://tools.superdatascience.com/blockchain/blockchain)

### Chaves Públicas

O Conceito de Chaves Públicas e Privadas, refere-se ao conceito de Criptografia assimétrica.
A Chave PRIVADA **NUNCA**, em **NENHUMA Hipótese**, deve ser revelada.
Com ela você deriva a chave PÚBLICA, e essa sim, é revelada.

Seguindo o desenho em anexo, imagine que Alice e Bob precisam trocar uma mensagem, e somente os 2 sabe seu conteúdo.

Alice envia sua chave pública para o BOB e ele criptografa a informação com a chave publica dele e da Alice.
Alice recebe a mensagem, e consegue recuperar seu conteúdo, abrindo com sua chave **PRIVADA**.

![Exemplo de Criptografia Simétrica](https://www.dropbox.com/scl/fi/5ioh9kfhmma4sxfayb8v3/chaves.jpg?rlkey=z320o5a089ace0yjoipt35yok&raw=)

### UTXO

UTXO é um protocolo utilizado, principalmente em redes Bitcoin.
O Conceito é de um Token Único, e caso você queira fracioná-lo, você envia para o destinatário o valor fracionado, e recebe o "troco" em sua própria carteira, com a diferença entre o valor fracionado e as despesas da transação.

### Account-Based

Account-Based é um conceito usado principalmente em redes Ethereum Alike.
O Conceito é muito mais simples de entender, pois ele debita os valores de envio e despesas de transações baseados no saldo total de sua conta.

## Transações

### Ciclo de vida de uma Tx

O Ciclo de vida de uma transação, dependerá da tecnologia blockchain.
No Caso de uma rede Bitcoin por exemplo, a transação só é efetivada, quando sua transação é transmitida e uma determinada quantidade de mineradodes (6 em uma rede de testes por exemplo), confirmam esta transação.
Em uma Rede Ethereum alike, dependerá do protocolo de consenso utilizado, não existe o conceito de mineração, mas sim, de validação dos blocos, que pode ser por votação dos nós (POA - Proof of Authority), Seleção aleatória de validadores, (Proof of Stake, neste caso, nós com maiores valores em carteira tem mais chances de serem selecionados) entre outros.

### Taxas

As taxas são valores pagos aos mantenedores das redes blockchain.
Tendo em mente que a rede Blockchain é um grande banco de dados, que necessita de infraestrutura, pessoas, energia e uma série de custos envolvidos, toda transação enviada para ser gravada na blockchain, o emissor paga as taxas de transmissão. em uma rede Ethereum alike, esta taxa é conhecida como *GAS*. As taxas variam de acordo com a rede, regras, utilização, tipo de informação a ser salva, tráfego no momento da solicitação entre outras variáveis.

## Blocos

### Criando uma Blockchain

Para criação de um bloco, o nó princial necessita informar e criar o Genesis block, e dentro dele ele possui o início das transações e suas regras, bem como o status inicial e seu hash inicial.

### Merkle Tree

Merkle Tree, nada mais é que uma estrutura de dados que otimiza hashes em uma estrutura de árvore. Ela agrupa 2 ou mais blocos de informação, fazendo com que eu chegue até a raíz, ou genesis block de uma forma muito mais rápida e eficiente, evitando calcular todo o caminho de dados gerados em um bloco. Isso dá escalabilidade em todo o processo.

## Consenso

### Proof-of-Work

Usado normalmente em redes Biticoin, é o conceito de mineiração.
Basicamente é a solução do desafio de encontrar uma sequencia de "0's" para criar o hash válido. Este processo consome muita energia, leva muito mais tempo, porém é muito mais seguro e virtualmente impossível de ser atacado ou economicamente inviável criar uma estrutura de ataque à rede.

### Proof-of-Stake

Consiste basicamente em fazer um sorteio aleatório dos nós participantes da rede, remunerando-os a cada bloco validado. Nós com maior volume armazenado em sua carteira terão mais chaces de serem selecionados.

### Proof-of-Authority

Normalmente utilizados em blockchains permissionadas com uma empresa ou entidade centralizadora. Ela será responsável por criar a cadeia de confiança entre os nós, e todos os blocos validados seguem as regras pelo órgão centralizador.
