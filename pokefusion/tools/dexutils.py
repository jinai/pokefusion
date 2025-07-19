import json


def generate_dex(target_base: str) -> None:
    with open("../config/dex_full.json", "r", encoding="utf-8") as f:
        pokedex_full = json.load(f)

    with open(f"../config/{target_base}_en.json", "r", encoding="utf-8") as f:
        dex_en = json.load(f)

    dex_fr = dict()
    dex_de = dict()

    for dex_id in dex_en:
        poke_en = dex_en[dex_id]
        for dex_entry in pokedex_full.values():
            if dex_entry["en"] == poke_en:
                dex_fr[dex_id] = dex_entry["fr"]
                dex_de[dex_id] = dex_entry["de"]
                break
        else:
            match dex_id:
                case "430":
                    dex_fr[dex_id] = "Plumeline-Flamenco"
                    dex_de[dex_id] = "Choreogel-Flamenco"
                case "431":
                    dex_fr[dex_id] = "Plumeline-Pom-Pom"
                    dex_de[dex_id] = "Choreogel-Cheerleading"
                case "432":
                    dex_fr[dex_id] = "Plumeline-Hula"
                    dex_de[dex_id] = "Choreogel-Hula"
                case "433":
                    dex_fr[dex_id] = "Plumeline-Buyō"
                    dex_de[dex_id] = "Choreogel-Buyo"

                case "464":
                    dex_fr[dex_id] = "Lougaroc-Diurne"
                    dex_de[dex_id] = "Wolwerock-Tag"
                case "465":
                    dex_fr[dex_id] = "Lougaroc-Nocturne"
                    dex_de[dex_id] = "Wolwerock-Nacht"

                case "466":
                    dex_fr[dex_id] = "Meloetta-Chant"
                    dex_de[dex_id] = "Meloetta-Gesangs"
                case "467":
                    dex_fr[dex_id] = "Meloetta-Danse"
                    dex_de[dex_id] = "Meloetta-Tanz"

                case "498":
                    dex_fr[dex_id] = "Météno-Météore"
                    dex_de[dex_id] = "Meteno-Meteor"
                case "499":
                    dex_fr[dex_id] = "Météno-Noyau"
                    dex_de[dex_id] = "Meteno-Kern"

                case _:
                    dex_fr[dex_id] = poke_en
                    dex_de[dex_id] = poke_en

    with open(f"../config/{target_base}_fr.json", "w", encoding="utf-8") as f:
        json.dump(dex_fr, f, ensure_ascii=False, indent=4)

    with open(f"../config/{target_base}_de.json", "w", encoding="utf-8") as f:
        json.dump(dex_de, f, ensure_ascii=False, indent=4)


def compare_sprites_pokedex():
    with open("../config/infinitedex_en.json", "r", encoding="utf-8") as f:
        dex_en = json.load(f)
    with open("../config/pokedex_en.json", "r", encoding="utf-8") as f:
        sprites = json.load(f)

    diff = [val for key, val in dex_en.items() if int(key) <= 565 and val != sprites[key]]
    print(diff)


if __name__ == "__main__":
    # compare_sprites_pokedex()
    generate_dex("infinitedex")
    generate_dex("pokedex")
