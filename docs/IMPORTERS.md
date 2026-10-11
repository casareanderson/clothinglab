# Bring your own importer

ClothingLab doesn't read your email or log in to shops. That's deliberate: reading someone's mailbox is a big
privacy and security step, and it shouldn't be switched on by default in a tool anyone can install.

If you want looks to use what you've bought, two options:

1. **By hand.** List pieces under `wardrobe:` in `profile.yaml`:

   ```yaml
   wardrobe:
     - {name: navy chore jacket, category: outer, colour: navy}
     - {name: white leather trainers, category: footwear, colour: white}
   ```

   `category` is one of `top`, `outer`, `bottom`, `footwear`; leave it out and it's worked out from the name.

2. **Your own importer.** Anything that writes that same `wardrobe:` list works: a script over an order-history
   export, a forwarded-email inbox, a spreadsheet. Keep it on your machine, keep the output to name, category and
   colour, and never store sizes, prices paid or addresses from the orders.

Looks use at most two owned pieces and always include at least one new one.
