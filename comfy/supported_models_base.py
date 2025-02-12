import torch
from . import model_base
from . import utils


def state_dict_key_replace(state_dict, keys_to_replace):
    for x in keys_to_replace:
        if x in state_dict:
            state_dict[keys_to_replace[x]] = state_dict.pop(x)
    return state_dict

def state_dict_prefix_replace(state_dict, replace_prefix):
    for rp in replace_prefix:
        replace = list(map(lambda a: (a, "{}{}".format(replace_prefix[rp], a[len(rp):])), filter(lambda a: a.startswith(rp), state_dict.keys())))
        for x in replace:
            state_dict[x[1]] = state_dict.pop(x[0])
    return state_dict


class ClipTarget:
    def __init__(self, tokenizer, clip):
        self.clip = clip
        self.tokenizer = tokenizer
        self.params = {}

class BASE:
    unet_config = {}
    unet_extra_config = {
        "num_heads": -1,
        "num_head_channels": 64,
    }

    clip_prefix = []
    clip_vision_prefix = None
    noise_aug_config = None

    @classmethod
    def matches(s, unet_config):
        for k in s.unet_config:
            if s.unet_config[k] != unet_config[k]:
                return False
        return True

    def v_prediction(self, state_dict):
        return False

    def inpaint_model(self):
        return self.unet_config["in_channels"] > 4

    def __init__(self, unet_config):
        self.unet_config = unet_config
        self.latent_format = self.latent_format()
        for x in self.unet_extra_config:
            self.unet_config[x] = self.unet_extra_config[x]

    def get_model(self, state_dict):
        if self.inpaint_model():
            return model_base.SDInpaint(self, v_prediction=self.v_prediction(state_dict))
        elif self.noise_aug_config is not None:
            return model_base.SD21UNCLIP(self, self.noise_aug_config, v_prediction=self.v_prediction(state_dict))
        else:
            return model_base.BaseModel(self, v_prediction=self.v_prediction(state_dict))

    def process_clip_state_dict(self, state_dict):
        return state_dict

