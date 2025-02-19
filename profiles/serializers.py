from dataclasses import field
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse
import tldextract
import urllib.parse
from decouple import config
from rest_framework import serializers,pagination

from .models import *


# client serializer
class ClientSerializer(serializers.ModelSerializer):
    # user_details = serializers.SerializerMethodField()

    # def get_user_details(self, obj):
    #     return {"email": obj.user.email}

    class Meta:
        model = Client
        fields = ["name", "email"]


class WorkFeedSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_id = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    def get_skills(self, obj):
        return [skill.name for skill in obj.owner.skill.all()]

    def get_owner_name(self, obj):
        return obj.owner.name

    def get_owner_id(self, obj):
        return obj.owner.pk

    def get_tags(self, obj):
        return [tags.name for tags in obj.tags.all()]

    class Meta:
        model = Work
        fields = [
            "weblink",
            "file",
            "demo_type",
            "owner_name",
            "owner_id",
            "details",
            "best_work",
            "name",
            "skills",
            "pk",
            "tags",
        ]


# ===================== project serializers ===================================


class ProjectSerializerMini(serializers.ModelSerializer):
    template = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    def get_template(self, obj):
        if obj.project_template is not None:
            return [obj.project_template.id, obj.project_template.name]
        return None

    def get_name(self, obj) -> Optional[str]:
        return obj.title or None

    class Meta:
        model = Project
        fields = [
            "pk",
            "title",
            "name",
            "stage",
            "template",
        ]


# ------------------------- project Demo Serializer ----------------------------


class ProjectDemoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    demo_type = serializers.SerializerMethodField()

    def get_demo_type(self, obj):
        if obj.link:
            parsed_url = urllib.parse.urlparse(obj.link)
            domain_parts = tldextract.extract(parsed_url.netloc.lower())
            root_domain = domain_parts.domain
            matching_demo_types = []
            for choice in DEMO_TYPE:
                if choice[0].lower().startswith(root_domain):
                    matching_demo_types.append(choice[0])
            if not matching_demo_types:
                matching_demo_types = Demo_Type.objects.filter(name__istartswith=root_domain).values_list('name', flat=True)
            if matching_demo_types:
                return matching_demo_types[0]
            return 'Other Document'
        elif obj.document:
            return obj.document.name.split('.')[-1]
        return 'UnDefined Link Or Document Type'

    def get_artist_name(self, obj):
        if obj.artist:
            return obj.artist.name
        return None
    def get_url(self, obj):
        return obj.document.url

    class Meta:
        model = ProjectDemo
        fields = [
            "id",
            "Title",
            "link",
            "artist",
            "artist_name",
            "demo_work",
            "project",
            "document",
            "demo_type",
            "url",
            "comment",
            "status",
        ]


class ChatBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatBot
        fields = ["status"]
        extra_kwargs = {"status": {"required": True}}


"""
    The default ModelSerializer .create() and .update() methods
     do not include support for writable nested representations.
"""

# -------------------- project serializer ---------------------------------------
class ProjectSerializer(serializers.ModelSerializer):
    template = serializers.SerializerMethodField()
    client_details = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    shortlisted_artists_details = serializers.SerializerMethodField()
    assigned_artists_details = serializers.SerializerMethodField()
    project_demos = serializers.SerializerMethodField()
    chatbot_status = ChatBotSerializer(required=False)
    links = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    def to_representation(self, instance):

        user = self.context['request'].user # Get current user
        client = instance.client.user # Get client of project
        visibility = instance.visibility # Get visibility of project
        if user.is_anonymous and visibility == 'public':
            # If user is anonymous and visibility is public, return full representation
            return super().to_representation(instance)
        elif user.is_anonymous and visibility == 'private':
            return {"message":"Please login as the client of this project to view this project details as this project is private"} # If user is anonymous and visibility is private, return empty representation
        role = Role.objects.get(user=user) # Get role of client
        if (role and (role.role == 'AM' or role.role == 'PM' or role.role == 'Artist')) or visibility == 'public' or user == client:
            # If client is an AM or project is public or user is the owner, return full representation
            return super().to_representation(instance)
        if visibility == 'private' and user != client:
            # If visibility is private and user is not the owner, return empty representation
            return {"message":"This project is private and only the owner can view this project"}

    def update(self, instance, validated_data):
        chat = ChatBot.objects.get(project=instance)
        # print(f"validated status {validated_data.get('chatbot_status').get('status')}")
        if "chatbot_status" in validated_data:
            chat.status = validated_data.pop("chatbot_status").get("status")
            chat.save()
        return super().update(instance, validated_data)

    def link_type(self,link):
        parsed_url = urllib.parse.urlparse(link)
        domain_parts = tldextract.extract(parsed_url.netloc.lower())
        root_domain = domain_parts.domain
        matching_demo_types = []
        for choice in DEMO_TYPE:
            if choice[0].lower().startswith(root_domain):
                matching_demo_types.append(choice[0])
        if not matching_demo_types:
            matching_demo_types = Demo_Type.objects.filter(name__istartswith=root_domain).values_list('name', flat=True)
        if matching_demo_types:
            return matching_demo_types[0]
        return 'Other Document'

    def get_links(self, obj):
        if obj.reference_links == "":
            return []
        if obj.reference_links is not None or obj.reference_links != "":
            links = obj.reference_links.split(",")
            return [
                {"link": link, "link_type": self.link_type(link)}
                for link in links
            ]

    def get_template(self, obj):
        if obj.project_template is not None:
            return [obj.project_template.id, obj.project_template.name]
        return None

    def get_client_details(self, obj):
        if obj.client is not None:
            return {
                "id": obj.client.id,
                "user_id": obj.client.user.id,
                "name": obj.client.name,
                "email": obj.client.email,
                "image": config("URL") + obj.client.image.url,
            }
        return None

    def get_shortlisted_artists_details(self, obj):
        return [
            {"id": artist.id, "name": artist.name}
            for artist in obj.shortlisted_artists.all()
        ]

    def get_assigned_artists_details(self, obj):
        artists = []
        for artist in obj.assigned_artists.all():
            artist_detail = {"id": artist.id, "name": artist.name}
            artist_detail["project_demos"] = [
                {
                    "demo_work": WorkFeedSerializer(
                        project_demo.demo_work, many=False
                    ).data,
                    "comment": project_demo.comment,
                    "status": project_demo.status,
                }
                for project_demo in obj.project_demos.filter(artist=artist)
            ]
            artists.append(artist_detail)
        return artists

    def get_name(self, obj) -> Optional[str]:
        return obj.title or None

    def get_project_demos(self, obj):
        return [
            ProjectDemoSerializer(demo, many=False).data
            for demo in obj.project_demos.all()
        ]

    def get_files(self, obj):
        if obj.files == "":
            return []
        files = obj.files.split(",")
        return [
            {"name": item.split()[0], "url": item.split()[1]}
            for item in files[:-1]
        ]
        # project_demos = []
        # print("project demo is -> ")
        # print(obj.projectdemo_Project.all())
        # for demo in obj.projectdemo_Project.all():
        #     prdemo = {"id":demo.id, "document":config("URL")+demo.document.url, "project":obj.id, "artist": demo.artist.id}
        #     prdemo["demo_work"] = demo.demo_work.id
        #     prdemo["comment"] = demo.comment
        #     project_demos.append(prdemo)
        # return project_demos

        # return [
        #     WorkFeedSerializer(work, many=False).data
        #     for work in obj.showcase_demos.all()
        # ]

    # ---------------------------------------------------------------------

    # def update(self, instance, validated_data):
    #     chatbot = validated_data.pop('chatbot_status')
    #     shop_obj = Shop.objects.filter(name=shop).first()
    #     if shop_obj:
    #         instance.shop = shop_obj
    #     return super().update(instance, validated_data)

    class Meta:
        model = Project
        fields = [
            "pk",
            "name",
            "title",
            "client",
            "client_details",
            "stage",
            "brief",
            "chatbot_status",
            "files",
            "reference_links",
            "links",
            "template",
            "shortlisted_artists_details",
            "shortlisted_artists",
            "assigned_artists_details",
            "production_solution",
            "project_template",
            "post_project_client_feedback",
            "project_demos",
            "comments",
            "contract_status",
            "solution_fee",
            "production_advance",
            "negotiated_advance",
            "final_advance",
            "advance_status",
            "assigned_artist_payouts",
            "artist_payout_status",
            "final_fee_settlement_status",
            "post_project_client_total_payout",
            "project_fee_Status",
            "artist_discussion_updates",
            "visibility",
        ]
        extra_kwargs = {
            "shortlisted_artists": {"write_only": True},
            "project_demos": {"write_only": True},
        }

class SaveChatFileSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()
    def get_files(self,obj):
        if obj.files == "":
            return []
        files = obj.files.split(",")
        return [
            {"name": item.split()[0], "url": item.split()[1]}
            for item in files[:-1]
        ]
    class Meta:
        model = Project
        fields = ['chat_file','files']

# ------------------------------------- project serializer end ---------------------------------------


class TemplateProjectsSerializer(serializers.ModelSerializer):
    def get_skills(self, obj):
        return [skill.name for skill in obj.skills.all()]

    skills = serializers.SerializerMethodField()

    class Meta:
        model = TemplateProjects
        fields = ["pk", "name", "details", "skills", "weblink", "file"]


# ===================== project serializers end ===================================


# ====================== artist manager serializers ===========================

class ProjectDemoLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDemo
        fields = ('id', 'Title', 'link', 'comment','artist','content_product')

    def create(self, validated_data):
        project_demo = ProjectDemo.objects.create(**validated_data)
        return project_demo


class ProjectDemoFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDemo
        fields = ('id', 'Title', 'document', 'comment','artist','content_product')

    def create(self, validated_data):
        project_demo = ProjectDemo.objects.create(**validated_data)
        return project_demo

class ProjectDemoListSerializer(serializers.ModelSerializer):
    demo_type = serializers.SerializerMethodField()
    artist_name = serializers.SerializerMethodField()
    collaborators = serializers.SerializerMethodField()
    content_product_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDemo
        fields = ('id', 'Title', 'link', 'document', 'comment', 'artist', 'artist_name', 'collaborators', 'demo_type','content_product_name')

    def get_content_product_name(self, obj):
        if obj.content_product:
            return obj.content_product.name
        return "No content product assigned"

    def get_demo_type(self, obj):
        if obj.link:
            parsed_url = urllib.parse.urlparse(obj.link)
            domain_parts = tldextract.extract(parsed_url.netloc.lower())
            root_domain = domain_parts.domain
            matching_demo_types = []
            for choice in DEMO_TYPE:
                if choice[0].lower().startswith(root_domain):
                    matching_demo_types.append(choice[0])
            if not matching_demo_types:
                matching_demo_types = Demo_Type.objects.filter(name__istartswith=root_domain).values_list('name', flat=True)
            if matching_demo_types:
                return matching_demo_types[0]
            return 'Other Document'
        elif obj.document:
            return obj.document.name.split('.')[-1]
        return 'UnDefined Link Or Document Type'

    def get_artist_name(self, obj):
        if obj.artist:
            return obj.artist.name
        return 'No artist assigned'

    def get_collaborators(self, obj):
        if obj.assigned_artists:
            return [{'id':collaborator.id,'name':collaborator.name} for collaborator in obj.assigned_artists.all()]
        return []

class AssignArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDemo
        fields = ('artist','assigned_artists',)

class UnAssignArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDemo
        fields = ('assigned_artists',)

class AssignProjectDemosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('project_demos',)

class AssignDemosProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDemo
        fields = ('project',)

def social_link_filter(self, obj):
    q = {}
    links = obj.social_links.split(",")

    for social in links:
        social = social.replace(" ", "")
        domain = urlparse(social).netloc

        domain = domain.split(".")

        if "facebook" in domain:
            q["facebook"] = social
        elif "instagram" in domain:
            q["instagram"] = social
        elif "twitter" in domain:
            q["twitter"] = social
        elif "youtube" in domain:
            q["youtube"] = social
        elif "linkedin" in domain:
            q["linkedin"] = social
        elif "spotify" in domain:
            q["spotify"] = social
        elif "soundcloud" in domain:
            q["soundcloud"] = social
        elif "tiktok" in domain:
            q["tiktok"] = social
        elif "twitch" in domain:
            q["twitch"] = social
        else:
            q["other"] = social

    return q


# update the artist

class WorkSerializer(serializers.ModelSerializer):
    tags = serializers.StringRelatedField(many=True)
    class Meta:
        model = Work
        fields = ['id', 'name', 'weblink','demo_type','tags']


# Serializers to display sills location and languages without pk
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['name']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['name']

class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['name']
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['name']

# Serializer for artist list display
class ArtistSerializer(serializers.ModelSerializer):
    works_links = serializers.SerializerMethodField()
    skill = SkillSerializer(many=True)
    location = LocationSerializer()
    languages = LanguageSerializer(many=True)
    genre = GenreSerializer(many=True)

    class Meta:
        model = Artist
        fields = ['id','name', 'artist_intro', 'email', 'phone', 'skill', 'location', 'languages',
                  'genre','profile_pic', 'profile_image', 'full_time', 'part_time', 'works_links','professional_rating',
                  'attitude_rating', 'budget_range']

    def get_works_links(self, obj):
        all_links = obj.works_links.all()
        work_links = all_links.filter(best_work=True).first()
        if work_links:
            return [{"id":work_links.id,"weblink":work_links.weblink,"demo_type":work_links.demo_type}]
        elif all_links:
            work_links = all_links.first()
            return [{"id":work_links.id,"weblink":work_links.weblink,"demo_type":work_links.demo_type}]
        else:
            return []

    # Get the real names of the ids to display on response object for artist list
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['skill'] = [s['name'] for s in representation['skill']]
        representation['languages'] = [l['name'] for l in representation['languages']]
        representation['genre'] = [g['name'] for g in representation['genre']]
        location = representation.get('location')
        if location:
            representation['location'] = location['name']
        return representation


class ArtistListPagination(pagination.PageNumberPagination):
    page_size = 10

class SkillSerializer(serializers.ModelSerializer):
    artist = serializers.SerializerMethodField()

    class Meta:
        model = Skill
        fields = ['pk', 'name', 'artist']

    def get_artist(self, skill):
        return skill.artist_set.count()


class ArtistProfileSerializer(serializers.ModelSerializer):
    works_links = WorkFeedSerializer(many=True)
    skills = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    # workLinks = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    genre = serializers.SerializerMethodField()
    def get_skills(self, obj):
        return [{"value":skill.id,"label":skill.name} for skill in obj.skill.all()]
    def get_manager(self, obj):
        if obj.has_manager and obj.manager:
            return {
                "name": obj.manager.name,
                "email": obj.manager.email,
                "phone": obj.manager.phone,
            }
        else:
            return []
    def get_language(self, obj):
        return [{"value":language.id,"label":language.name} for language in obj.languages.all()]
    def get_genre(self, obj):
        return [{"value": gen.id, "label": gen.name} for gen in obj.genre.all()]
    # def get_workLinks(self, obj):
    #     return [[work.weblink] for work in obj.works_links.all()]
    def get_location(self, obj):
        if obj.location is not None:
            return {"value": obj.location.id, "label": obj.location.name}
        return None
    class Meta:
        model = Artist
        fields = [
            "id",
            "name",
            "artist_intro",
            "age",
            "email",
            "phone",
            "skills",
            "location",
            "genre",
            "language",
            "works_links",
            "profile_pic",
            "profile_image",
            "social_links",
            "social_profile",
            "relocation",
            "other_arts",
            "full_time",
            "part_time",
            "has_agreement",
            "agreement",
            "min_budget",
            "max_budget",
            "ctc_per_annum",
            "best_link",
            "has_manager",
            "manager",
            "budget_range",
            "budget_idea",
            "am_notes",
            "pm_notes",
            "professional_rating",
            "attitude_rating",
        ]



class ArtistFilterSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()
    works_links = WorkFeedSerializer(many=True)  # serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    genre = serializers.SerializerMethodField()

    def get_skills(self, obj):
        return [skill.name for skill in obj.skill.all()]

    def get_social_links(self, obj):
        return social_link_filter(self, obj)

    def get_manager(self, obj):
        if obj.has_manager and obj.manager:
            return {
                "name": obj.manager.name,
                "email": obj.manager.email,
                "phone": obj.manager.phone,
            }
        else:
            return []

    def get_languages(self, obj):
        return [language.name for language in obj.languages.all()]

    def get_works_links(self, obj):
        print("i called")
        return [[work.weblink] for work in obj.works_links.all()]

    def get_location(self, obj):
        if obj.location is not None:
            return {"id": obj.location.id, "name": obj.location.name}
        return None

    def get_genre(self, obj):
        return [{"id": gen.id, "name": gen.name} for gen in obj.genre.all()]

    class Meta:
        model = Artist
        fields = [
            "id",
            "name",
            "age",
            "email",
            "phone",
            "skills",
            "location",
            "profile_pic",
            "profile_image",
            "genre",
            "languages",
            "works_links",
            "social_links",
            "social_profile",
            "relocation",
            "min_budget",
            "max_budget",
            "ctc_per_annum",
            "full_time",
            "best_link",
            "has_manager",
            "manager",
            "budget_idea",
            "am_notes",
            "professional_rating",
            "attitude_rating",
        ]


class ManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manager
        fields = "__all__"

class WorksLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Work
        fields = [
            "pk",
            "weblink",
            "file",
            "demo_type",
            "owner",
            "details",
            "best_work",
            "show_in_top_feed",
            "name",
        ]

class ArtistActionSerializer(serializers.ModelSerializer):
    works_links = WorksLinkSerializer(many=True, required=False)
    class Meta:
        model = Artist
        fields = [
            "id",
            "name",
            "profile_pic",
            "profile_image",
            "artist_intro",
            "location",
            "age",
            "email",
            "phone",
            "skill",
            "genre",
            "languages",
            "works_links",
            "social_links",
            "has_manager",
            "manager",
            "budget_idea",
            "am_notes",
            "professional_rating",
            "attitude_rating",
            "full_time",
            "ctc_per_annum"
        ]

    def update(self, instance, validated_data):
        works_links_data = validated_data.pop("works_links", [])
        instance = super().update(instance, validated_data)
        for work_link_data in works_links_data:
            pk = work_link_data.get("pk", None)
            if pk:
                work_link = Work.objects.get(pk=pk)
                serializer = WorksLinkSerializer(work_link, data=work_link_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return instance
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('name',)


class WorkLinkSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    class Meta:
        model = Work
        fields = ('pk', 'name', 'details', 'weblink', 'show_in_top_feed', 'is_demo', 'best_work', 'demo_type','tags')
    def to_representation(self, instance):
        representation =  super().to_representation(instance)
        representation['tags'] = [t['name'] for t in representation['tags']]
        return representation


class ArtistWorkLinkSerializer(serializers.ModelSerializer):
    works_links = WorkLinkSerializer(many=True)

    class Meta:
        model = Artist
        fields = ('name', 'works_links')

class WorkLinkCreateSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=Tag.objects.all(),
        required=False
    )

    def to_internal_value(self, data):
        # Capitalize the tags before validating and saving them
        if 'tags' in data:
            capitalized_tags = [tag.capitalize() for tag in data['tags']]
            data['tags'] = capitalized_tags

        return super().to_internal_value(data)

    class Meta:
        model = Work
        fields = (
            'id', 'name', 'details', 'weblink', 'show_in_top_feed',
            'is_demo', 'best_work', 'owner', 'from_client', 'is_active',
            'file', 'demo_type', 'tags'
        )


# ====================== product manager serializers ===========================
class ArtistFeedbackSerializer(serializers.ModelSerializer):
    artist_details = serializers.SerializerMethodField()

    def get_artist_details(self, obj):
        if obj.artist is not None:
            return {"id": obj.artist.id, "name": obj.artist.name}
        return None

    class Meta:
        model = ArtistFeedback
        fields = [
            "artist",
            "artist_details",
            "pre_project_feedbace",
            "on_project_feedback",
            "post_project_feedback",
        ]


class ProjectFeeSerializers(serializers.ModelSerializer):
    project_details = serializers.SerializerMethodField()
    assigned_artist_payouts_details = serializers.SerializerMethodField()

    def get_project_details(self, obj):
        if obj.project is not None:
            return {
                "id": obj.project.id,
                "project": str(obj.project),
                "brief": obj.project.brief,
            }
        return None

    def get_assigned_artist_payouts_details(self, obj):
        return [
            {"id": artist.id, "name": artist.name}
            for artist in obj.assigned_artist_payouts.all()
        ]

    class Meta:
        model = ProjectFee
        fields = [
            "project",
            "client",
            "project_details",
            "solution_fee",
            "production_advance",
            "negotiated_advance",
            "advance_status",
            "final_advance",
            "project_fee_Status",
            "assigned_artist_payouts",
            "assigned_artist_payouts_details",
            "artist_payout_status",
            "final_fee_settlement_status",
            "post_project_client_total_payout",
            "project_fee_Status",
        ]


class ArtistRequestSerializers(serializers.ModelSerializer):
    skills_details = serializers.SerializerMethodField()
    location_details = serializers.SerializerMethodField()
    languages_details = serializers.SerializerMethodField()
    genre_details = serializers.SerializerMethodField()
    project_details = serializers.SerializerMethodField()
    shortlisted_artists_details = serializers.SerializerMethodField()
    rejected_artists_details = serializers.SerializerMethodField()

    def get_skills_details(self, obj):
        return [skill.name for skill in obj.skill.all()]

    def get_location_details(self, obj):
        if obj.location is not None:
            return {"id": obj.location.id, "name": obj.location.name}
        return None

    def get_genre_details(self, obj):
        return [{"id": gen.id, "name": gen.name} for gen in obj.genre.all()]

    def get_languages_details(self, obj):
        return [language.name for language in obj.languages.all()]

    def get_project_details(self, obj):
        if obj.project is not None:
            return {
                "id": obj.project.id,
                "name": obj.project.title,
            }
        return None

    def get_shortlisted_artists_details(self, obj):
        return [
            {"id": artist.id, "name": artist.name}
            for artist in obj.shortlisted_artists.all()
        ]

    def get_rejected_artists_details(self, obj):
        return [
            {"id": artist.id, "name": artist.name}
            for artist in obj.rejected_artists.all()
        ]

    class Meta:
        model = ArtistRequest
        fields = ['id',
                  'skills_details',
                  'location_details',
                  'languages_details',
                  'genre_details',
                  'project_details',
                  'shortlisted_artists_details',
                  'rejected_artists_details',
                  "other_performin_arts",
                    "budget_range",
                    "budget_idea",
                    "production_hiring",
                    "service_hiring",
                    "target",
                    "comments",
                    "hiring_status",
                  ]
