import pandas as pd
import panel as pn
from rhymer import TextCollection, Lexicon, Rhymer, HebrewC, Loc

NUM_RHYMES = 30


def Verse(loc: Loc, text: HebrewC) -> pn.Column:
    return pn.pane.Markdown(f"{text.__str__()} {loc}")


def MyCard(index: int, title: HebrewC, verses: list[Loc]) -> pn.Column:

    verses_items = [
        Verse(*verses[0]),
        *[
            item
            for i in range(1, len(verses))
            for item in (pn.layout.Divider(), Verse(*verses[i]))
        ],
    ]
    card_kwargs = dict(
        title=f"{index}. {title.__str__()}",
        sizing_mode="stretch_width",
        styles=dict(margin="15px 30px"),
    )

    if len(verses) < 6:
        items = verses_items
    else:
        items = [pn.Feed(*verses_items, sizing_mode="stretch_both", height=None)]
        card_kwargs["height"] = 600

    return pn.Column(pn.Card(*items, **card_kwargs, collapsed=True,))


class App:

    layout: pn.Column
    input: pn.widgets.TextInput
    cards_feed: pn.Feed
    card_holder: pn.Card
    rhymer: Rhymer
    spinner: pn.indicators.LoadingSpinner
    rhymes: list[tuple[HebrewC, list[Loc]]]

    def __init__(self):
        self.layout = self.panel_app()
        texts = TextCollection("bib", "../data")
        lex = Lexicon(texts)
        self.rhymer = Rhymer(lex)
        self.rhymes = []
        self.spinner = pn.indicators.LoadingSpinner(
            value=True, size=20, name="Loading..."
        )

    def create_cards(self, begin, end, add_spinner=False):
        cards = [
            MyCard(i + 1, word, verses)
            for i, (word, verses) in zip(range(begin, end), self.rhymes[begin:end])
        ] 
        if add_spinner:
            cards += [self.spinner]
        return cards

    def update_input(self, event):
        """
        Update the card with the input value
        """
        self.cards_feed = self._create_feed()
        self.card_holder.objects = [self.spinner]
        self.rhymes = list(self.rhymer.rhymes_verses(self.input.value))
        self.card_holder.title = f"Output: {len(self.rhymes)} Rhymes Found"
        self.cards_feed.objects = self.create_cards(0, NUM_RHYMES, NUM_RHYMES < len(self.rhymes))
        self.card_holder.objects = [self.cards_feed]

    def update_scroll(self, event):
        if self.cards_feed.visible_range is None:
            print("none event")
            return
        _, end = self.cards_feed.visible_range
        num_cards_curr = len(self.cards_feed)
        if end > num_cards_curr - (NUM_RHYMES / 3):
            new_end = num_cards_curr + NUM_RHYMES
            new_cards = self.create_cards(num_cards_curr, new_end, new_end < len(self.rhymes))
            self.cards_feed.pop(-1)
            self.cards_feed.extend(new_cards)

    def _create_feed(self):
        feed = pn.Feed(
            scroll_button_threshold=20, height=500, styles=dict(padding="15px"),
        )
        feed.param.watch(self.update_scroll, "visible_range")
        return feed

    def _create_input(self):
        input = pn.widgets.TextInput(
            name="Text Input", placeholder="Enter a string here..."
        )
        input.param.watch(self.update_input, "value")
        return input

    def panel_app(self) -> pn.Column:
        """ """

        self.input = self._create_input()

        self.cards_feed = self._create_feed

        self.card_holder = pn.Card(
            self.cards_feed,
            title="Output",
            collapsible=False,
            sizing_mode="stretch_width",
            styles=dict(margin="10px", text_align="center"),
        )

        return pn.Column(
            pn.pane.Markdown("# Home Page"),
            self.input,
            self.card_holder,
            styles=dict(direction="rtl"),
        )


if __name__ == "__main__":
    pn.serve(
        panels=lambda: App().layout,
        port=5006,
        title="App",
        show=False,
        autoreload=True,
        session_history=1,
        user_key="sub",
        allow_websocket_origin=["*"],
    )
