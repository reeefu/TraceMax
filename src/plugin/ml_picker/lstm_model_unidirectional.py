from .lstm_base import _import_torch, make_attention_pooling, load_model as _load


def build_model(input_dim=1, hidden1=128, hidden2=64, hidden3=32,
                dense_dim=64, dropout=0.35):
    torch, nn = _import_torch()

    class SeismicLSTMUnidirectional(nn.Module):
        def __init__(self):
            super().__init__()
            self.bn_input = nn.BatchNorm1d(input_dim)

            self.lstm1 = nn.LSTM(
                input_size=input_dim, hidden_size=hidden1,
                batch_first=True, bidirectional=False, num_layers=1,
            )
            self.ln1 = nn.LayerNorm(hidden1)
            self.dropout1 = nn.Dropout(dropout)

            self.lstm2 = nn.LSTM(
                input_size=hidden1, hidden_size=hidden2,
                batch_first=True, bidirectional=False, num_layers=1,
            )
            self.ln2 = nn.LayerNorm(hidden2)
            self.dropout2 = nn.Dropout(dropout)

            self.lstm3 = nn.LSTM(
                input_size=hidden2, hidden_size=hidden3,
                batch_first=True, bidirectional=False, num_layers=1,
            )
            self.dropout3 = nn.Dropout(dropout)

            self.attention = make_attention_pooling(hidden3)

            self.fc = nn.Sequential(
                nn.Linear(hidden3, dense_dim),
                nn.ReLU(),
                nn.Dropout(dropout * 0.67),
                nn.Linear(dense_dim, 1),
            )

        def forward(self, x, return_attention=False):
            x = x.permute(0, 2, 1)
            x = self.bn_input(x)
            x = x.permute(0, 2, 1)

            out, _ = self.lstm1(x)
            out = self.ln1(out)
            out = self.dropout1(out)
            out, _ = self.lstm2(out)
            out = self.ln2(out)
            out = self.dropout2(out)
            out, _ = self.lstm3(out)
            out = self.dropout3(out)

            context, attn_weights = self.attention(out)
            pred = self.fc(context).squeeze(-1)

            if return_attention:
                return pred, attn_weights
            return pred

        def count_parameters(self):
            return sum(p.numel() for p in self.parameters() if p.requires_grad)

    return SeismicLSTMUnidirectional()


def load_model(model_path):
    return _load(build_model, model_path)
