# Enhanced_Audio

O **Enhanced_Audio** é um cog para o Redbot que aprimora o cog original de áudio. Ele adiciona embeds mais bonitos e interativos, substitui e melhora alguns comandos do cog padrão, proporcionando uma experiência melhor para os usuários ao controlar a reprodução de músicas.

## Recursos

- **Interface Interativa:** Utiliza botões customizados (play/pause, stop, skip, repeat, shuffle, etc.) para facilitar o controle da reprodução.
- **Melhores Embeds:** Exibe informações da música atual, fila de reprodução e status com embeds mais informativos e visualmente agradáveis.
- **Comandos Aprimorados:** Novos comandos que substituem os comandos padrão do cog Audio:
  - `eplay [query]`: Pesquisa e reproduz a música com uma interface aprimorada.
  - `enow`: Mostra a música atual com controles interativos.
  - `equeue`: Exibe a fila de reprodução em páginas.
  - `eskip`: Pula a música atual e atualiza a interface.
- **Verificação de Inatividade:** Limpa mensagens antigas e atualiza periodicamente o embed interativo.

## Instalação

1. **Pré-requisitos:**  
   - Certifique-se de que o cog `Audio` original do Redbot esteja instalado e devidamente configurado. O Enhanced_Audio depende dele para funcionar corretamente.

2. **Instalação do Enhanced_Audio:**  
   - Faça o download ou clone este repositório para a pasta de cogs do seu Redbot.
   - Verifique se as dependências necessárias (como `discord.py`, `lavalink`, etc.) estão instaladas no ambiente onde o Redbot está rodando.
   - Carregue o cog utilizando o comando (geralmente em seu Discord):  
     ```
     [p]load Enhanced_Audio
     ```

## Uso

- **`eplay [query]`**  
  Pesquisa e reproduz a música especificada, exibindo uma interface aprimorada com controles interativos.

- **`enow`**  
  Mostra a música atualmente em reprodução, com botões para pausar, pular, repetir, etc.

- **`equeue`**  
  Exibe a fila de reprodução em formato paginado, permitindo a navegação pela lista de músicas.

- **`eskip`**  
  Pula a música atual e atualiza o embed com informações da nova faixa em reprodução.

## Configuração

O cog utiliza a configuração do Redbot para armazenar dados específicos por guilda, como os estados de repetição e modo aleatório. Ele também inicia uma tarefa em background que verifica a inatividade para limpar mensagens antigas.

## Contribuição

Contribuições são bem-vindas! Caso queira sugerir melhorias ou reportar problemas, por favor, abra uma _issue_ ou envie um _pull request_ neste repositório.

