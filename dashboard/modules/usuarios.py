# ============================================================
# usuarios.py — Gerenciamento de usuários (MySQL)
# ============================================================

from modules.config import get_secret
from modules.vias import USUARIOS as USUARIOS_PADRAO


def _conectar():
    import mysql.connector
    return mysql.connector.connect(
        host                = get_secret("MYSQL_HOST"),
        port                = int(get_secret("MYSQL_PORT")),
        database            = get_secret("MYSQL_DATABASE"),
        user                = get_secret("MYSQL_USER"),
        password            = get_secret("MYSQL_PASSWORD"),
        connection_timeout  = 10,
        autocommit          = False,
        ssl_verify_cert     = False,
        ssl_verify_identity = False,
    )


def _garantir_tabela(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INT AUTO_INCREMENT PRIMARY KEY,
            nome      VARCHAR(100) NOT NULL UNIQUE,
            ativo     TINYINT DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def carregar_usuarios():
    """Retorna lista de nomes de usuários ativos. Fallback para lista padrão."""
    try:
        conn   = _conectar()
        cursor = conn.cursor()
        _garantir_tabela(cursor)
        conn.commit()
        cursor.execute("SELECT nome FROM usuarios WHERE ativo = 1 ORDER BY nome")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            return [r[0] for r in rows]
        # Tabela vazia → semear com os padrões
        return _seed_e_retornar()
    except Exception:
        return list(USUARIOS_PADRAO)


def _seed_e_retornar():
    """Insere usuários padrão no banco se a tabela estiver vazia."""
    try:
        conn   = _conectar()
        cursor = conn.cursor()
        _garantir_tabela(cursor)
        for nome in USUARIOS_PADRAO:
            cursor.execute("INSERT IGNORE INTO usuarios (nome) VALUES (%s)", (nome,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass
    return list(USUARIOS_PADRAO)


def adicionar_usuario(nome: str):
    """Adiciona usuário ativo. Retorna (ok, mensagem)."""
    nome = nome.strip()
    if not nome:
        return False, "Nome não pode ser vazio."
    try:
        conn   = _conectar()
        cursor = conn.cursor()
        _garantir_tabela(cursor)
        # Reativar se existia desativado
        cursor.execute(
            "INSERT INTO usuarios (nome, ativo) VALUES (%s, 1) "
            "ON DUPLICATE KEY UPDATE ativo = 1",
            (nome,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Usuário '{nome}' adicionado."
    except Exception as e:
        return False, str(e)


def renomear_usuario(nome_antigo: str, nome_novo: str):
    """Renomeia usuário. Retorna (ok, mensagem)."""
    nome_novo = nome_novo.strip()
    if not nome_novo:
        return False, "Novo nome não pode ser vazio."
    if nome_antigo == nome_novo:
        return False, "Nome igual ao atual."
    try:
        conn   = _conectar()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET nome = %s WHERE nome = %s AND ativo = 1",
            (nome_novo, nome_antigo)
        )
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        if affected == 0:
            return False, "Usuário não encontrado."
        return True, f"'{nome_antigo}' renomeado para '{nome_novo}'."
    except Exception as e:
        return False, str(e)


def remover_usuario(nome: str):
    """Desativa usuário. Retorna (ok, mensagem)."""
    try:
        conn   = _conectar()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE usuarios SET ativo = 0 WHERE nome = %s", (nome,)
        )
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        if affected == 0:
            return False, "Usuário não encontrado."
        return True, f"Usuário '{nome}' removido."
    except Exception as e:
        return False, str(e)
