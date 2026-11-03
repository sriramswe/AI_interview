import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

def generate_performance_chart(session_scores: list[float], dates: list[str]) -> bytes:
    """Generates an in-memory PNG chart tracking candidate progress over time."""
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(8, 4))
    
    sns.lineplot(x=dates, y=session_scores, marker="o", color="#2563eb", linewidth=2.5, ax=ax)
    ax.set_title("Interview Performance Trend", fontsize=14, pad=12)
    ax.set_xlabel("Session Timeline", fontsize=10)
    ax.set_ylabel("Score (0 - 100)", fontsize=10)
    ax.set_ylim(0, 105)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()