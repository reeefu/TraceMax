

def _import_torch():
    import torch
    import torch.nn as nn
    return torch, nn


def make_attention_pooling(hidden_dim):
    torch, nn = _import_torch()

    class AttentionPooling(nn.Module):
        def __init__(self):
            super().__init__()
            self.attention = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.Tanh(),
                nn.Linear(hidden_dim, 1, bias=False),
            )

        def forward(self, lstm_output):
            scores = self.attention(lstm_output)
            weights = torch.softmax(scores, dim=1)
            context = torch.sum(weights * lstm_output, dim=1)
            weights = weights.squeeze(-1)
            return context, weights

    return AttentionPooling()


def load_model(build_fn, model_path):
    torch, _ = _import_torch()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = build_fn()
    state = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, torch, device
