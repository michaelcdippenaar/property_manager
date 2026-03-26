import graphene

from apps.leases.schema import (
    Query as LeasesQuery,
    Mutation as LeasesMutation,
)


class Query(LeasesQuery, graphene.ObjectType):
    pass


class Mutation(LeasesMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
