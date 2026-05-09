import os
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai
from keep_alive import keep_alive

# 環境変数の読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
if GEMINI_API_KEY and GEMINI_API_KEY != "ここにGeminiのAPIキーを貼り付けてください":
    genai.configure(api_key=GEMINI_API_KEY)
    # モデルの初期化 (最新の高速モデルを使用)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

# プロンプトの読み込み
def load_system_prompt():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "あなたはコミュニティを盛り上げるファシリテーターです。以下の履歴から新しい話題を1つ提案してください。"

# Discord Botの初期化 (Message Content Intentを有効化)
intents = discord.Intents.default()
intents.message_content = True
# プレフィックスを「!」に設定
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready!")

@bot.command(name="topic")
async def generate_topic(ctx):
    """チャット履歴を読み込んで話題を生成するコマンド"""
    if not model:
        await ctx.send("エラー: Gemini APIキーが正しく設定されていません。.envファイルを確認してください。")
        return
        
    # 考え中... というインジケータを出す
    async with ctx.typing():
        try:
            messages = []
            # サーバー内のすべてのテキストチャンネルをループ
            for channel in ctx.guild.text_channels:
                # 閲覧権限があるかチェック
                if channel.permissions_for(ctx.guild.me).read_message_history:
                    try:
                        # 各チャンネルから過去150件を取得
                        async for msg in channel.history(limit=150):
                            # bot自身の発言とコマンドは除外
                            if not msg.author.bot and not msg.content.startswith("!"):
                                messages.append(msg)
                    except Exception:
                        pass # 取得エラーのチャンネルはスキップ
            
            if not messages:
                await ctx.send("チャット履歴が全く見つかりませんでした。")
                return
                
            # 全チャンネルの履歴からランダムに100件を抽出（全体的な過去の話題を拾うため）
            if len(messages) > 100:
                sampled_messages = random.sample(messages, 100)
            else:
                sampled_messages = messages
                
            # 時間順（古い順）に並び替え
            sampled_messages.sort(key=lambda m: m.created_at)
            
            # 履歴のテキスト化
            history_text = ""
            for msg in sampled_messages:
                # チャンネル名も付与して文脈をわかりやすくする
                history_text += f"[#{msg.channel.name}] {msg.author.display_name}: {msg.content}\n"
            
            # システムプロンプトの読み込み
            system_prompt = load_system_prompt()
            
            # Geminiへ渡すプロンプトを作成
            full_prompt = f"{system_prompt}\n\n【最近のチャット履歴】\n{history_text}"
            
            # 話題の生成
            response = model.generate_content(full_prompt)
            
            # 結果を送信
            await ctx.send(response.text)
            
        except discord.Forbidden:
            await ctx.send("エラー: メッセージ履歴を読み取る権限がありません。ボットの権限設定を確認してください。")
        except Exception as e:
            print(f"Error during topic generation: {e}")
            await ctx.send("話題の生成中にエラーが発生しました。しばらくしてからもう一度お試しください。")

if __name__ == "__main__":
    # Webサーバーをバックグラウンドで起動
    keep_alive()
    
    if not DISCORD_TOKEN or DISCORD_TOKEN == "ここにDiscordボットのトークンを貼り付けてください":
        print("エラー: Discordボットのトークンが設定されていません。.envファイルを確認してください。")
    else:
        bot.run(DISCORD_TOKEN)
