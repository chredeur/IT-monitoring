"""
Service de notification Discord via webhooks.
Envoie les nouvelles entrées RSS vers Discord.
"""
import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
import discord
from discord import Webhook
from discord.ui import View, Button


class DiscordNotifier:
    """Gère l'envoi de notifications vers des webhooks Discord."""

    # Couleurs par type de contenu
    COLORS = {
        'announcements': 0x5865F2,  # Bleu Discord
        'releases': 0x57F287,       # Vert
        'commits': 0xFEE75C,        # Jaune
        'default': 0x99AAB5         # Gris
    }

    # Icônes par type
    ICONS = {
        'announcements': '📢',
        'releases': '🚀',
        'commits': '💻',
        'default': '📰'
    }

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger('it_monitoring.discord_notifier')
        self.session: Optional[aiohttp.ClientSession] = None
        self.discord_config = config.get('discord', {})
        self.enabled = self.discord_config.get('enabled', False)
        self.rate_limit_delay = self.discord_config.get('batch_delay_seconds', 2)

    async def set_session(self, session: aiohttp.ClientSession):
        """Définit la session HTTP à utiliser."""
        self.session = session

    def is_enabled(self) -> bool:
        """Vérifie si les notifications Discord sont activées."""
        return self.enabled and bool(self.discord_config.get('webhooks'))

    async def notify_new_entries(self, new_entries: List[Dict]) -> Dict[str, int]:
        """
        Envoie des notifications pour les nouvelles entrées.

        Args:
            new_entries: Liste des nouvelles entrées à notifier

        Returns:
            Dict avec le nombre de succès/échecs par webhook
        """
        if not self.is_enabled() or not new_entries:
            return {'sent': 0, 'failed': 0}

        if not self.session:
            self.logger.error("HTTP session not initialized")
            return {'sent': 0, 'failed': len(new_entries)}

        results = {'sent': 0, 'failed': 0}
        webhooks = self.discord_config.get('webhooks', [])

        for entry in new_entries:
            for webhook_config in webhooks:
                if self._should_notify(entry, webhook_config):
                    success = await self._send_notification(entry, webhook_config)
                    if success:
                        results['sent'] += 1
                    else:
                        results['failed'] += 1

                    # Rate limiting entre les envois
                    await asyncio.sleep(self.rate_limit_delay)

        if results['sent'] > 0:
            self.logger.info(f"Discord notifications sent: {results['sent']} success, {results['failed']} failed")

        return results

    def _should_notify(self, entry: Dict, webhook_config: Dict) -> bool:
        """
        Vérifie si une entrée doit être notifiée pour ce webhook.

        Args:
            entry: L'entrée RSS à vérifier
            webhook_config: Configuration du webhook

        Returns:
            True si l'entrée doit être notifiée
        """
        # Vérifier la catégorie
        allowed_categories = webhook_config.get('categories', [])
        if allowed_categories:
            entry_category = entry.get('category_key', '').lower()
            if entry_category not in [c.lower() for c in allowed_categories]:
                return False

        # Vérifier le type
        allowed_types = webhook_config.get('types', [])
        if allowed_types:
            entry_type = entry.get('feed_type', '').lower()
            if entry_type not in [t.lower() for t in allowed_types]:
                return False

        return True

    async def _send_notification(self, entry: Dict, webhook_config: Dict) -> bool:
        """
        Envoie une notification pour une entrée vers un webhook.

        Args:
            entry: L'entrée RSS à notifier
            webhook_config: Configuration du webhook

        Returns:
            True si l'envoi a réussi
        """
        webhook_url = webhook_config.get('url')
        if not webhook_url:
            return False

        try:
            # Créer le webhook Discord
            webhook = Webhook.from_url(webhook_url, session=self.session)

            # Construire l'embed
            embed = self._build_embed(entry)

            # Construire la vue avec bouton
            view = None
            site_url = self.discord_config.get('site_url')
            if site_url:
                entry_id = entry.get('id', '')
                encoded_id = urllib.parse.quote(entry_id, safe='')
                site_link = f"{site_url}?article={encoded_id}"

                view = View()
                button = Button(
                    label="Voir sur IT Monitoring",
                    url=site_link,
                    style=discord.ButtonStyle.link,
                    emoji="🔗"
                )
                view.add_item(button)

            # Contenu avec mention si configuré
            content = None
            mention_role = webhook_config.get('mention_role')
            if mention_role:
                content = f"<@&{mention_role}>"

            # Envoyer le message
            await webhook.send(
                content=content,
                embed=embed,
                view=view
            )
            return True

        except discord.HTTPException as e:
            if e.status == 429:
                # Rate limited
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 5
                self.logger.warning(f"Discord rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._send_notification(entry, webhook_config)
            else:
                self.logger.error(f"Discord webhook failed: {e}")
                return False
        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {e}")
            return False

    def _build_embed(self, entry: Dict) -> discord.Embed:
        """
        Construit un embed Discord pour une entrée.

        Args:
            entry: L'entrée RSS

        Returns:
            discord.Embed
        """
        feed_type = entry.get('feed_type', 'default')
        icon = self.ICONS.get(feed_type, self.ICONS['default'])
        color = self.COLORS.get(feed_type, self.COLORS['default'])

        # Titre avec icône
        title = entry.get('title', 'Sans titre')
        if len(title) > 256:
            title = title[:253] + '...'

        # Description (summary)
        description = entry.get('summary', '')
        if description:
            description = self._clean_html(description)
            if len(description) > 300:
                description = description[:297] + '...'

        # Créer l'embed
        embed = discord.Embed(
            title=f"{icon} {title}",
            description=description if description else None,
            color=color,
            url=entry.get('link'),
            timestamp=datetime.now(timezone.utc)
        )

        # Footer
        embed.set_footer(
            text=f"{entry.get('category', 'IT Monitoring')} • {entry.get('feed_name', 'RSS Feed')}"
        )

        # Auteur si disponible
        if entry.get('author'):
            embed.set_author(name=entry['author'])

        # Champs
        type_labels = {
            'announcements': 'Annonce',
            'releases': 'Release',
            'commits': 'Commit'
        }
        type_label = type_labels.get(feed_type, feed_type.capitalize())

        embed.add_field(name="Type", value=type_label, inline=True)
        embed.add_field(name="Source", value=entry.get('feed_name', 'Unknown'), inline=True)

        return embed

    def _clean_html(self, text: str) -> str:
        """Nettoie le HTML basique d'un texte."""
        import re
        # Supprimer les tags HTML
        clean = re.sub(r'<[^>]+>', '', text)
        # Décoder les entités HTML courantes
        clean = clean.replace('&nbsp;', ' ')
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&#39;', "'")
        # Nettoyer les espaces multiples
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    async def send_test_message(self, webhook_url: str) -> bool:
        """
        Envoie un message de test vers un webhook.

        Args:
            webhook_url: URL du webhook Discord

        Returns:
            True si l'envoi a réussi
        """
        if not self.session:
            self.logger.error("HTTP session not initialized")
            return False

        try:
            webhook = Webhook.from_url(webhook_url, session=self.session)

            embed = discord.Embed(
                title="✅ Test de connexion IT Monitoring",
                description="Ce message confirme que le webhook Discord est correctement configuré.",
                color=0x57F287,
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text="IT Monitoring Dashboard")
            embed.add_field(name="Status", value="Connecté", inline=True)
            embed.add_field(
                name="Notifications",
                value="Actives" if self.is_enabled() else "Désactivées",
                inline=True
            )

            # Bouton de test
            view = None
            site_url = self.discord_config.get('site_url')
            if site_url:
                view = View()
                button = Button(
                    label="Ouvrir IT Monitoring",
                    url=site_url,
                    style=discord.ButtonStyle.link,
                    emoji="🔗"
                )
                view.add_item(button)

            await webhook.send(embed=embed, view=view)
            return True

        except Exception as e:
            self.logger.error(f"Error sending test message: {e}")
            return False
