from comfy import sd1_clip
import torch
import os

class SDXLClipG(sd1_clip.SD1ClipModel):
    def __init__(self, device="cpu", max_length=77, freeze=True, layer="penultimate", layer_idx=None):
        textmodel_json_config = os.path.join(os.path.dirname(os.path.realpath(__file__)), "clip_config_bigg.json")
        super().__init__(device=device, freeze=freeze, textmodel_json_config=textmodel_json_config)
        self.empty_tokens = [[49406] + [49407] + [0] * 75]
        self.text_projection = torch.nn.Parameter(torch.empty(1280, 1280))
        self.layer_norm_hidden_state = False
        if layer == "last":
            pass
        elif layer == "penultimate":
            layer_idx = -1
            self.clip_layer(layer_idx)
        elif self.layer == "hidden":
            assert layer_idx is not None
            assert abs(layer_idx) < 32
            self.clip_layer(layer_idx)
        else:
            raise NotImplementedError()

    def clip_layer(self, layer_idx):
        if layer_idx < 0:
            layer_idx -= 1 #The real last layer of SD2.x clip is the penultimate one. The last one might contain garbage.
        if abs(layer_idx) >= 32:
            self.layer = "hidden"
            self.layer_idx = -2
        else:
            self.layer = "hidden"
            self.layer_idx = layer_idx

class SDXLClipGTokenizer(sd1_clip.SD1Tokenizer):
    def __init__(self, tokenizer_path=None, embedding_directory=None):
        super().__init__(tokenizer_path, pad_with_end=False, embedding_directory=embedding_directory, embedding_size=1280)


class SDXLTokenizer(sd1_clip.SD1Tokenizer):
    def __init__(self, embedding_directory=None):
        self.clip_l = sd1_clip.SD1Tokenizer(embedding_directory=embedding_directory)
        self.clip_g = SDXLClipGTokenizer(embedding_directory=embedding_directory)

    def tokenize_with_weights(self, text:str, return_word_ids=False):
        out = {}
        out["g"] = self.clip_g.tokenize_with_weights(text, return_word_ids)
        out["l"] = self.clip_l.tokenize_with_weights(text, return_word_ids)
        return out

    def untokenize(self, token_weight_pair):
        return self.clip_g.untokenize(token_weight_pair)

class SDXLClipModel(torch.nn.Module):
    def __init__(self, device="cpu"):
        super().__init__()
        self.clip_l = sd1_clip.SD1ClipModel(layer="hidden", layer_idx=11, device=device)
        self.clip_l.layer_norm_hidden_state = False
        self.clip_g = SDXLClipG(device=device)

    def clip_layer(self, layer_idx):
        self.clip_l.clip_layer(layer_idx)
        self.clip_g.clip_layer(layer_idx)

    def encode_token_weights(self, token_weight_pairs):
        token_weight_pairs_g = token_weight_pairs["g"]
        token_weight_pairs_l = token_weight_pairs["l"]
        g_out, g_pooled = self.clip_g.encode_token_weights(token_weight_pairs_g)
        l_out, l_pooled = self.clip_l.encode_token_weights(token_weight_pairs_l)
        return torch.cat([l_out, g_out], dim=-1), g_pooled

class SDXLRefinerClipModel(torch.nn.Module):
    def __init__(self, device="cpu"):
        super().__init__()
        self.clip_g = SDXLClipG(device=device)

    def clip_layer(self, layer_idx):
        self.clip_g.clip_layer(layer_idx)

    def encode_token_weights(self, token_weight_pairs):
        token_weight_pairs_g = token_weight_pairs["g"]
        g_out, g_pooled = self.clip_g.encode_token_weights(token_weight_pairs_g)
        return g_out, g_pooled

