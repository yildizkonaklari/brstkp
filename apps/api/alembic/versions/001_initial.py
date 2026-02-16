"""initial

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # symbols
    op.create_table('symbols',
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('list_start_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('symbol')
    )
    op.create_index(op.f('ix_symbols_symbol'), 'symbols', ['symbol'], unique=False)

    # prices_daily
    op.create_table('prices_daily',
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('turnover_tl', sa.Float(), nullable=True),
        sa.Column('adj_close', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['symbols.symbol'], ),
        sa.PrimaryKeyConstraint('symbol', 'date')
    )

    # index_daily
    op.create_table('index_daily',
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('return_1d', sa.Float(), nullable=True),
        sa.Column('ema50', sa.Float(), nullable=True),
        sa.Column('ema200', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('date')
    )

    # features_daily
    op.create_table('features_daily',
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('ema50', sa.Float(), nullable=True),
        sa.Column('ema200', sa.Float(), nullable=True),
        sa.Column('atr14_pct', sa.Float(), nullable=True),
        sa.Column('dd60', sa.Float(), nullable=True),
        sa.Column('rs_3m', sa.Float(), nullable=True),
        sa.Column('rs_6m', sa.Float(), nullable=True),
        sa.Column('bo_120', sa.Float(), nullable=True),
        sa.Column('vol_surge', sa.Float(), nullable=True),
        sa.Column('up_ratio_20', sa.Float(), nullable=True),
        sa.Column('adv20_tl', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['symbols.symbol'], ),
        sa.PrimaryKeyConstraint('symbol', 'date')
    )

    # scores_daily
    op.create_table('scores_daily',
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('potential_score', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=True),
        sa.Column('explain_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['symbols.symbol'], ),
        sa.PrimaryKeyConstraint('symbol', 'date')
    )

    # top10_daily
    op.create_table('top10_daily',
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('final_score', sa.Float(), nullable=False),
        sa.Column('universe_tag', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['symbol'], ['symbols.symbol'], ),
        sa.PrimaryKeyConstraint('date', 'rank')
    )

    # backtest_runs
    op.create_table('backtest_runs',
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('params_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('run_id')
    )

    # backtest_trades
    op.create_table('backtest_trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=True),
        sa.Column('slippage', sa.Float(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.run_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # backtest_equity_curve
    op.create_table('backtest_equity_curve',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('equity', sa.Float(), nullable=False),
        sa.Column('benchmark_equity', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.run_id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('backtest_equity_curve')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
    op.drop_table('top10_daily')
    op.drop_table('scores_daily')
    op.drop_table('features_daily')
    op.drop_table('index_daily')
    op.drop_table('prices_daily')
    op.drop_index(op.f('ix_symbols_symbol'), table_name='symbols')
    op.drop_table('symbols')
