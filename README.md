# DualSense Studio

[![Empacotar](https://github.com/ayramesteodosio/dualsense-studio/actions/workflows/empacotar.yml/badge.svg)](https://github.com/ayramesteodosio/dualsense-studio/actions/workflows/empacotar.yml)

Outra interface para o [Painel do DualSense](https://github.com/ayramesteodosio/dualsense-painel), com o
controle desenhado na tela. O desenho acompanha o controle ao vivo: cor da barra de luz, LEDs, botões
apertados e pressão dos gatilhos. Toda a parte que conversa com o controle vem do painel; este repo é só a
interface.

<img src="docs/capturas/controle.png" alt="Aba Controle">

## Funções

- Modo carregar: no cabo USB, o controle some do sistema, até da Steam, e a barra pulsa enquanto carrega.
  Pode entrar sozinho ao ligar o cabo ou pelo atalho PS + Options.
- Luz de carga: cor, estilo (respirar, fixa, piscar), duração do ciclo, intensidade e o que fazer quando
  encher.
- Barra de luz com roda de cores, modo que mostra a bateria, LEDs do jogador, luz do microfone e teste de
  vibração.
- Gatilhos adaptativos: os sete efeitos, com gráfico do curso e pressão ao vivo.
- Teste: botões, analógicos (zona morta, drift, circularidade), gatilhos, touchpad, giroscópio,
  acelerômetro, vibração por motor, áudio (alto-falante, fone e microfone) e taxa de atualização, com
  relatório em Markdown.
- Informações: modelo, cor de fábrica, placa (BDM), número de série, firmware, hardware, MAC, conexão e
  bateria.
- Perfis, histórico de bateria, aviso de bateria baixa e desligamento por inatividade no Bluetooth.
- Segundo plano: ao fechar a janela o app continua rodando (dá para desligar nos Ajustes), com modo
  carregar automático, avisos de bateria e atalho funcionando. "Iniciar com o sistema" é opcional, no
  instalador do Windows ou nos Ajustes. Só um app usa o controle por vez: abrir o outro faz o primeiro
  soltar o controle e fechar.

<table>
<tr>
<td><img src="docs/capturas/luzes.png" alt="Aba Luzes"></td>
<td><img src="docs/capturas/gatilhos.png" alt="Aba Gatilhos"></td>
</tr>
<tr>
<td><img src="docs/capturas/teste.png" alt="Aba Teste"></td>
<td><img src="docs/capturas/info.png" alt="Aba Informações"></td>
</tr>
</table>

## Baixar

Pegue o arquivo do seu sistema na [última versão](https://github.com/ayramesteodosio/dualsense-studio/releases/latest):

| Sistema | Arquivo | Como instalar |
|---|---|---|
| Windows 10 e 11 | `DualSense-Studio-windows.exe` | Abra e siga o instalador |
| macOS com chip Apple | `DualSense-Studio-macos-arm64.dmg` | Abra e arraste o app para Aplicativos |
| macOS com Intel | `DualSense-Studio-macos-intel.dmg` | Abra e arraste o app para Aplicativos |
| Ubuntu, Debian, Mint e derivados | `dualsense-studio_<versão>_all.deb` | Dois cliques, ou `sudo apt install ./dualsense-studio_*.deb` |

No Windows, o instalador oferece instalar junto o [HidHide](https://github.com/nefarius/HidHide), que deixa o modo
carregar esconder o controle dos jogos e da Steam. Os apps avisam quando sai uma versão nova e se atualizam com um clique.

O app não tem assinatura digital, então o sistema avisa na primeira vez:

- Windows: em "O Windows protegeu o computador", clique em **Mais informações** e **Executar assim mesmo**.
- macOS: se o Mac não deixar abrir, vá em **Ajustes do Sistema > Privacidade e Segurança** e clique em
  **Abrir Mesmo Assim**.

Windows e macOS ainda não foram testados em máquinas reais, só com um controle simulado e com o pacote
rodando no Linux. Se algo não funcionar, abra uma issue.

## Rodar pelo código no Linux

O painel precisa estar ao lado deste repo (ou no caminho da variável `DUALSENSE_PAINEL`).

```sh
git clone https://github.com/ayramesteodosio/dualsense-painel.git
git clone https://github.com/ayramesteodosio/dualsense-studio.git
cd dualsense-studio
./instalar.sh          # instala o painel também, com a regra do udev
./dualsense-studio     # ou "DualSense Studio" no menu
```

Precisa de GTK 3 e WebKitGTK 4.0 ou 4.1. 

## Sistemas

| | Linux | Windows | macOS |
|---|---|---|---|
| Janela | GTK e WebKit | pywebview e WebView2 | pywebview e WebKit |
| Acesso ao controle | hidraw, sysfs e usbfs | hidapi | hidapi |
| Esconder dos jogos no modo carregar | sim | com o [HidHide](https://github.com/nefarius/HidHide) | sim (abertura exclusiva) |
| Áudio do controle | PulseAudio | sounddevice | sounddevice |
| Desligar pelo Bluetooth | sim | não | não |

No Windows, sem o HidHide, o modo carregar só apaga as luzes e acompanha a bateria. Com ele, o app pede
permissão de administrador ao esconder e mostrar o controle.

Fechar a janela no Windows e no macOS encerra o app e devolve o controle ao sistema. No Linux, no modo
carregar, o app continua em segundo plano.

## Como funciona

- `ui/fonte/index.html` é a fonte da interface.
- `ui/index.html` é a interface final, gerada a partir da anterior por
  `python3 ferramentas/ajustar_interface.py ui/fonte/index.html ui/index.html`. O script acrescenta
  cor, placa e série em Informações, ajusta o teste e liga a ponte com o app. Aberta direto no navegador,
  ela roda com um controle simulado (teclas `D`, `B` e `F`).
- `dualsense_studio/app.py` é a janela GTK com WebKit (Linux); `dualsense_studio/web.py` é a janela
  pywebview (Windows e macOS).
- `dualsense_studio/bridge.py` traduz as mensagens da interface para o `Session` do painel.

Foto do controle (opcional): Com `--foto`, o script troca o desenho por uma foto: coloque
`ui/dualsense-base.png` e a máscara da barra de luz `ui/dualsense-lightbar.png` e gere
`ui/index-foto.html`. Se os três arquivos existirem, o app usa essa versão. Use uma foto sua, não
material de divulgação da Sony. Por enquanto esses arquivos ficam fora do git.

Mensagens: Da interface para o app, `window.webkit.messageHandlers.ds.postMessage(...)` no Linux ou
`window.pywebview.api.send(...)` fora dele, sempre com `JSON.stringify({type, payload})`: `ready`,
`setLightbar`, `setPlayerLeds`, `setMicLed`, `setTrigger`, `testRumble`, `rumble`, `setCharging`,
`setChargeGlow`, `setAutoCharge`, `setChargeLight`, `setLightbarMode`, `setShortcut`, `setLowBattery`,
`setIdleOff`, `disconnectBluetooth`, `saveProfile`, `applyProfile`, `deleteProfile`, `audioTone`,
`micStart`, `micStop` e `saveReport`. Do app para a interface, `window.dsReceive(msg)`: `state`,
`input` (até 60 por segundo), `info`, `history`, `micLevel` e `toast`.

Para depurar a interface dentro do app: `DS_DEVTOOLS=1 ./dualsense-studio` (botão direito, Inspecionar).

## Gerar o .exe e o .app

O fluxo `.github/workflows/empacotar.yml` gera os pacotes no GitHub Actions ao criar uma tag `v*` (e
publica em Releases) ou manualmente pela aba Actions. Ele baixa o `dualsense-painel` da mesma conta.

Localmente, em cada sistema:

```sh
pip install -r requirements.txt pyinstaller
DUALSENSE_PAINEL=../dualsense-painel python -m PyInstaller --noconfirm empacotar/dualsense-studio.spec
```

Os ícones saem de `dados/com.ayrames.DualSenseStudio.svg` com `python3 ferramentas/gerar_icones.py`
(precisa de cairosvg e Pillow).

## Aviso

Projeto independente, sem relação com a Sony Interactive Entertainment. DualSense, PlayStation e
DualShock são marcas da Sony Interactive Entertainment Inc. e aparecem aqui só para indicar com qual
controle o app funciona.

## Testes

```sh
PYTHONPATH=../dualsense-painel python3 -m unittest discover -s tests -t .
```
