from decimal import Decimal
from django.db import models
from django.urls import reverse
from netbox.models import NetBoxModel
from virtualization.models import VirtualMachine


class VDIBillingProfile(NetBoxModel):
    """Pricing profile for a VDI class (e.g. Standard, GPU Workstation, Persistent).
    Monthly cost is calculated from VM specs (vCPU, RAM, optional GPU surcharge)."""

    name = models.CharField(max_length=100, unique=True, verbose_name='Profile Name')
    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Base Price ($/month)',
        help_text='Fixed monthly amount regardless of VM resources.',
    )
    vcpu_price = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Price per vCPU ($/month)',
    )
    ram_price_per_gb = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Price per GB RAM ($/month)',
    )
    gpu_surcharge = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00'),
        verbose_name='GPU Surcharge ($/month)',
        help_text='Added when the VM custom field "gpu" is set to a truthy value.',
    )
    description = models.TextField(blank=True, verbose_name='Description')

    class Meta:
        ordering = ['name']
        verbose_name = 'VDI Billing Profile'
        verbose_name_plural = 'VDI Billing Profiles'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_vdi_billing:vdibillingprofile', args=[self.pk])

    def calculate_cost(self, vm: VirtualMachine) -> float:
        """Calculate monthly cost for a given VM."""
        cost = float(self.base_price)
        cost += float(self.vcpu_price) * float(vm.vcpus or 0)
        cost += float(self.ram_price_per_gb) * float(vm.memory or 0) / 1024.0
        if vm.custom_field_data.get('gpu'):
            cost += float(self.gpu_surcharge)
        return round(cost, 2)


class VDIAssignment(NetBoxModel):
    """Links a NetBox VM to billing information: cost center, department,
    pricing profile, and an optional fixed price override."""

    virtual_machine = models.OneToOneField(
        to=VirtualMachine,
        on_delete=models.CASCADE,
        related_name='vdi_billing',
        verbose_name='Virtual Machine',
    )
    profile = models.ForeignKey(
        to=VDIBillingProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assignments',
        verbose_name='Billing Profile',
        help_text='Profile used to calculate cost from VM specs.',
    )
    cost_center = models.CharField(
        max_length=100, blank=True,
        verbose_name='Cost Center',
        help_text='Any identifier for the cost center (number, name, team, etc.).',
    )
    department = models.CharField(
        max_length=200, blank=True,
        verbose_name='Department',
    )
    assigned_to = models.CharField(
        max_length=200, blank=True,
        verbose_name='Assigned To',
        help_text='Username or team responsible for this VM.',
    )
    cost_override = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Fixed Price ($/month)',
        help_text='Overrides the profile calculation with a fixed monthly amount.',
    )
    notes = models.TextField(blank=True, verbose_name='Notes')

    class Meta:
        ordering = ['virtual_machine__name']
        verbose_name = 'VDI Assignment'
        verbose_name_plural = 'VDI Assignments'

    def __str__(self):
        cc = self.cost_center or 'No Cost Center'
        return f'{self.virtual_machine.name} – {cc}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_vdi_billing:vdiassignment', args=[self.pk])

    @property
    def cost_monthly(self) -> float:
        """Monthly cost: fixed price > profile > 0."""
        if self.cost_override is not None:
            return round(float(self.cost_override), 2)
        if self.profile:
            return self.profile.calculate_cost(self.virtual_machine)
        return 0.0

    @property
    def cost_yearly(self) -> float:
        return round(self.cost_monthly * 12, 2)

    @property
    def pricing_source(self) -> str:
        if self.cost_override is not None:
            return 'Fixed Price'
        if self.profile:
            return f'Profile: {self.profile.name}'
        return '—'
